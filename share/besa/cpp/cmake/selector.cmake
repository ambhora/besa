# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
include_guard(GLOBAL)
include("${CMAKE_CURRENT_LIST_DIR}/internal.cmake")

# Parse the named callback contract used by custom selector functions.
#
# A selector callback is called by BESA as:
#
#   my_selector(
#     OUTPUT_VARIABLE <result-variable>
#     ERROR_VARIABLE  <error-variable>
#     NAME            <object-being-selected>
#     FEATURES        <resolved-enabled-features...>
#   )
#
# The callback sets the variable named by OUTPUT_VARIABLE to TRUE/FALSE in PARENT_SCOPE.  It may set
# ERROR_VARIABLE to a diagnostic when the selector itself cannot be evaluated.  FALSE with an empty
# error simply means that the object is not selected.
function(besa_selector_arguments_parse)
  cmake_parse_arguments(ARG "" "PREFIX" "ARGUMENTS" ${ARGN})
  _besa_require_no_unparsed("besa_selector_arguments_parse" "${ARG_UNPARSED_ARGUMENTS}")
  _besa_require_value("besa_selector_arguments_parse" "PREFIX" "${ARG_PREFIX}")

  cmake_parse_arguments(PARSED "" "OUTPUT_VARIABLE;ERROR_VARIABLE;NAME" "FEATURES" ${ARG_ARGUMENTS})
  _besa_require_no_unparsed("selector callback" "${PARSED_UNPARSED_ARGUMENTS}")
  _besa_require_value("selector callback" "OUTPUT_VARIABLE" "${PARSED_OUTPUT_VARIABLE}")
  _besa_require_value("selector callback" "ERROR_VARIABLE" "${PARSED_ERROR_VARIABLE}")
  _besa_require_value("selector callback" "NAME" "${PARSED_NAME}")

  set("${ARG_PREFIX}_OUTPUT_VARIABLE" "${PARSED_OUTPUT_VARIABLE}" PARENT_SCOPE)
  set("${ARG_PREFIX}_ERROR_VARIABLE" "${PARSED_ERROR_VARIABLE}" PARENT_SCOPE)
  set("${ARG_PREFIX}_NAME" "${PARSED_NAME}" PARENT_SCOPE)
  set("${ARG_PREFIX}_FEATURES" "${PARSED_FEATURES}" PARENT_SCOPE)
endfunction()

function(_besa_selector_check_atom ATOM ENABLED_FEATURES OUTPUT_VARIABLE)
  _besa_feature_base_name("${ATOM}" _feature _negated)
  if("${_feature}" STREQUAL "")
    _besa_fatal("feature selector" "empty feature name")
  endif()

  if("${_feature}" IN_LIST ENABLED_FEATURES)
    set(_enabled TRUE)
  else()
    set(_enabled FALSE)
  endif()

  if(_negated)
    if(_enabled)
      set(_enabled FALSE)
    else()
      set(_enabled TRUE)
    endif()
  endif()
  set("${OUTPUT_VARIABLE}" "${_enabled}" PARENT_SCOPE)
endfunction()

# Evaluate a WHEN selector.  This is internal because public functions expose it through a named
# `WHEN ...` argument rather than asking users to call the evaluator directly.
#
# Supported selector forms:
#   WHEN ALL_OF feature-a ~feature-b
#   WHEN ANY_OF feature-a feature-b
#   WHEN REGEX "^project-"
#   WHEN FUNCTION my_selector
function(_besa_selector_evaluate NAME WHEN_ARGUMENTS OUTPUT_VARIABLE)
  get_property(_features GLOBAL PROPERTY BESA_ENABLED_FEATURES)

  if(NOT WHEN_ARGUMENTS)
    set("${OUTPUT_VARIABLE}" TRUE PARENT_SCOPE)
    return()
  endif()

  list(GET WHEN_ARGUMENTS 0 _kind)
  list(REMOVE_AT WHEN_ARGUMENTS 0)

  if(_kind STREQUAL "ALL_OF" OR _kind STREQUAL "ANY_OF")
    if(NOT WHEN_ARGUMENTS)
      _besa_fatal("feature selector" "${_kind} requires at least one feature")
    endif()

    set(_seen)
    foreach(_atom IN LISTS WHEN_ARGUMENTS)
      _besa_feature_base_name("${_atom}" _base _negated)
      if("${_base}" IN_LIST _seen)
        _besa_fatal("feature selector" "feature '${_base}' appears more than once")
      endif()
      list(APPEND _seen "${_base}")
    endforeach()

    if(_kind STREQUAL "ALL_OF")
      set(_result TRUE)
      foreach(_atom IN LISTS WHEN_ARGUMENTS)
        _besa_selector_check_atom("${_atom}" "${_features}" _matches)
        if(NOT _matches)
          set(_result FALSE)
          break()
        endif()
      endforeach()
    else()
      set(_result FALSE)
      foreach(_atom IN LISTS WHEN_ARGUMENTS)
        _besa_selector_check_atom("${_atom}" "${_features}" _matches)
        if(_matches)
          set(_result TRUE)
          break()
        endif()
      endforeach()
    endif()

  elseif(_kind STREQUAL "REGEX")
    list(LENGTH WHEN_ARGUMENTS _count)
    if(NOT _count EQUAL 1)
      _besa_fatal("feature selector" "REGEX requires exactly one regular expression")
    endif()
    list(GET WHEN_ARGUMENTS 0 _regex)
    set(_result FALSE)
    foreach(_feature IN LISTS _features)
      if("${_feature}" MATCHES "${_regex}")
        set(_result TRUE)
        break()
      endif()
    endforeach()

  elseif(_kind STREQUAL "FUNCTION")
    list(LENGTH WHEN_ARGUMENTS _count)
    if(NOT _count EQUAL 1)
      _besa_fatal("feature selector" "FUNCTION requires exactly one function name")
    endif()
    list(GET WHEN_ARGUMENTS 0 _function)
    if(NOT COMMAND "${_function}")
      _besa_fatal("feature selector" "function '${_function}' does not exist")
    endif()

    set(_result FALSE)
    set(_error "")
    cmake_language(
      CALL "${_function}"
      OUTPUT_VARIABLE _result
      ERROR_VARIABLE _error
      NAME "${NAME}"
      FEATURES ${_features}
    )
    if(_error)
      _besa_fatal("feature selector '${_function}'" "${_error}")
    endif()

  else()
    _besa_fatal(
      "feature selector"
      "unknown selector '${_kind}'. Expected ANY_OF, ALL_OF, REGEX, or FUNCTION"
    )
  endif()

  set("${OUTPUT_VARIABLE}" "${_result}" PARENT_SCOPE)
endfunction()
