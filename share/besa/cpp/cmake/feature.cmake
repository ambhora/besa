# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
include_guard(GLOBAL)
include("${CMAKE_CURRENT_LIST_DIR}/internal.cmake")

# Declare every feature which the project understands.  Features describe optional project topology
# or capability.  They are declared before besa_configure_complete() and cannot be added afterwards.
function(besa_features_add)
  _besa_require_config_open("besa_features_add")
  cmake_parse_arguments(ARG "" "" "FEATURES" ${ARGN})
  _besa_require_no_unparsed("besa_features_add" "${ARG_UNPARSED_ARGUMENTS}")
  if(NOT ARG_FEATURES)
    _besa_fatal("besa_features_add" "FEATURES requires at least one feature")
  endif()

  foreach(_feature IN LISTS ARG_FEATURES)
    if("${_feature}" MATCHES "^~")
      _besa_fatal("besa_features_add" "declared feature '${_feature}' must not use '~'")
    endif()
    _besa_append_unique(BESA_DECLARED_FEATURES "${_feature}" "besa_features_add")
  endforeach()
endfunction()

# Declare the features which are enabled when PROJECT_FEATURES does not override them.
function(besa_features_default)
  _besa_require_config_open("besa_features_default")
  cmake_parse_arguments(ARG "" "" "FEATURES" ${ARGN})
  _besa_require_no_unparsed("besa_features_default" "${ARG_UNPARSED_ARGUMENTS}")

  get_property(_declared GLOBAL PROPERTY BESA_DECLARED_FEATURES)
  foreach(_feature IN LISTS ARG_FEATURES)
    if("${_feature}" MATCHES "^~")
      _besa_fatal("besa_features_default" "default feature '${_feature}' must not use '~'")
    endif()
    if(NOT "${_feature}" IN_LIST _declared)
      _besa_fatal("besa_features_default" "unknown feature '${_feature}'")
    endif()
    _besa_append_unique(BESA_DEFAULT_FEATURES "${_feature}" "besa_features_default")
  endforeach()
endfunction()

# Parse the named callback contract used by feature constraints.
#
# A constraint callback should begin with:
#
#   besa_feature_constraint_arguments_parse(PREFIX ARG ARGUMENTS ${ARGN})
#
# It then reads ARG_FEATURES and writes TRUE/FALSE to ${ARG_OUTPUT_VARIABLE} and a human-readable
# diagnostic to ${ARG_ERROR_VARIABLE}, both in PARENT_SCOPE.
function(besa_feature_constraint_arguments_parse)
  cmake_parse_arguments(ARG "" "PREFIX" "ARGUMENTS" ${ARGN})
  _besa_require_no_unparsed("besa_feature_constraint_arguments_parse" "${ARG_UNPARSED_ARGUMENTS}")
  _besa_require_value("besa_feature_constraint_arguments_parse" "PREFIX" "${ARG_PREFIX}")

  cmake_parse_arguments(PARSED "" "OUTPUT_VARIABLE;ERROR_VARIABLE" "FEATURES" ${ARG_ARGUMENTS})
  _besa_require_no_unparsed("feature constraint callback" "${PARSED_UNPARSED_ARGUMENTS}")
  _besa_require_value(
    "feature constraint callback" "OUTPUT_VARIABLE" "${PARSED_OUTPUT_VARIABLE}"
  )
  _besa_require_value("feature constraint callback" "ERROR_VARIABLE" "${PARSED_ERROR_VARIABLE}")

  set("${ARG_PREFIX}_OUTPUT_VARIABLE" "${PARSED_OUTPUT_VARIABLE}" PARENT_SCOPE)
  set("${ARG_PREFIX}_ERROR_VARIABLE" "${PARSED_ERROR_VARIABLE}" PARENT_SCOPE)
  set("${ARG_PREFIX}_FEATURES" "${PARSED_FEATURES}" PARENT_SCOPE)
endfunction()

function(besa_register_feature_constraint)
  _besa_require_config_open("besa_register_feature_constraint")
  cmake_parse_arguments(ARG "" "FUNCTION" "" ${ARGN})
  _besa_require_no_unparsed("besa_register_feature_constraint" "${ARG_UNPARSED_ARGUMENTS}")
  _besa_require_value("besa_register_feature_constraint" "FUNCTION" "${ARG_FUNCTION}")
  if(NOT COMMAND "${ARG_FUNCTION}")
    _besa_fatal(
      "besa_register_feature_constraint"
      "constraint function '${ARG_FUNCTION}' does not exist"
    )
  endif()
  _besa_append_unique(BESA_FEATURE_CONSTRAINTS "${ARG_FUNCTION}" "besa_register_feature_constraint")
endfunction()

function(_besa_toolchain_language FEATURE OUTPUT_VARIABLE)
  if(FEATURE STREQUAL "toolchain-c")
    set(_language C)
  elseif(FEATURE STREQUAL "toolchain-cpp")
    set(_language CXX)
  elseif(FEATURE STREQUAL "toolchain-cuda")
    set(_language CUDA)
  elseif(FEATURE STREQUAL "toolchain-hip")
    set(_language HIP)
  elseif(FEATURE STREQUAL "toolchain-fortran")
    set(_language Fortran)
  elseif(FEATURE STREQUAL "toolchain-asm")
    set(_language ASM)
  else()
    set(_language "")
  endif()
  set("${OUTPUT_VARIABLE}" "${_language}" PARENT_SCOPE)
endfunction()

function(_besa_resolve_features OUTPUT_VARIABLE)
  get_property(_declared GLOBAL PROPERTY BESA_DECLARED_FEATURES)
  get_property(_defaults GLOBAL PROPERTY BESA_DEFAULT_FEATURES)

  set(_enabled ${_defaults})
  set(_seen)

  foreach(_entry IN LISTS PROJECT_FEATURES)
    if("${_entry}" STREQUAL "")
      continue()
    endif()
    _besa_feature_base_name("${_entry}" _feature _negated)

    # PROJECT_FEATURES is a set of overrides, not an imperative sequence.  A feature therefore may
    # appear at most once, even if one occurrence is positive and the other uses '~'.
    if("${_feature}" IN_LIST _seen)
      _besa_fatal(
        "besa_configure_complete"
        "feature '${_feature}' is specified more than once in PROJECT_FEATURES"
      )
    endif()
    list(APPEND _seen "${_feature}")

    if(NOT "${_feature}" IN_LIST _declared)
      _besa_fatal(
        "besa_configure_complete"
        "unknown feature '${_feature}'. Declared features are: ${_declared}"
      )
    endif()

    if(_negated)
      list(REMOVE_ITEM _enabled "${_feature}")
    elseif(NOT "${_feature}" IN_LIST _enabled)
      list(APPEND _enabled "${_feature}")
    endif()
  endforeach()

  set("${OUTPUT_VARIABLE}" "${_enabled}" PARENT_SCOPE)
endfunction()

function(_besa_run_feature_constraints ENABLED_FEATURES)
  get_property(_constraints GLOBAL PROPERTY BESA_FEATURE_CONSTRAINTS)
  foreach(_constraint IN LISTS _constraints)
    set(_valid FALSE)
    set(_error "")
    cmake_language(
      CALL "${_constraint}"
      OUTPUT_VARIABLE _valid
      ERROR_VARIABLE _error
      FEATURES ${ENABLED_FEATURES}
    )

    if(NOT _valid)
      if(_error)
        _besa_fatal("feature constraint '${_constraint}'" "${_error}")
      else()
        _besa_fatal("feature constraint '${_constraint}'" "constraint rejected the feature set")
      endif()
    endif()
  endforeach()
endfunction()

function(_besa_publish_feature_booleans ENABLED_FEATURES)
  get_property(_declared GLOBAL PROPERTY BESA_DECLARED_FEATURES)
  foreach(_feature IN LISTS _declared)
    _besa_normalize_name("${_feature}" _normalized)
    if("${_feature}" IN_LIST ENABLED_FEATURES)
      set(_value TRUE)
    else()
      set(_value FALSE)
    endif()
    set("PROJECT_FEATURE_${_normalized}" "${_value}" CACHE INTERNAL "Resolved BESA feature")
  endforeach()
endfunction()

macro(_besa_enable_toolchain_languages ENABLED_FEATURES_VARIABLE)
  set(_besa_toolchain_languages)
  set(_besa_enable_asm FALSE)

  foreach(_feature IN LISTS ${ENABLED_FEATURES_VARIABLE})
    if("${_feature}" MATCHES "^toolchain-")
      _besa_toolchain_language("${_feature}" _language)
      if(NOT _language)
        _besa_fatal(
          "besa_configure_complete"
          "feature '${_feature}' uses the reserved 'toolchain-' prefix, but this BESA version does "
          "not know how to enable its CMake language"
        )
      endif()

      # CMake recommends enabling ASM last so that an already enabled C or CXX compiler can also be
      # considered for assembly sources. Preserve that ordering regardless of feature declaration
      # or override order.
      if(_language STREQUAL "ASM")
        set(_besa_enable_asm TRUE)
      elseif(NOT "${_language}" IN_LIST _besa_toolchain_languages)
        list(APPEND _besa_toolchain_languages "${_language}")
      endif()
    endif()
  endforeach()

  if(_besa_enable_asm)
    list(APPEND _besa_toolchain_languages ASM)
  endif()

  foreach(_language IN LISTS _besa_toolchain_languages)
    enable_language("${_language}")
    get_property(_enabled_languages GLOBAL PROPERTY BESA_ENABLED_LANGUAGES)
    if(NOT "${_language}" IN_LIST _enabled_languages)
      set_property(GLOBAL APPEND PROPERTY BESA_ENABLED_LANGUAGES "${_language}")
    endif()
  endforeach()
endmacro()

# Render the resolved configuration in one concise configure-time summary.  These are the values
# BESA actually uses after defaults, explicit overrides, and constraints have been processed.
function(_besa_configuration_summary LIST_FEATURES LIST_DEVTOOLS LIST_TEST_MODES LIST_WARNINGS)
  foreach(_name IN ITEMS FEATURES DEVTOOLS TEST_MODES WARNINGS)
    set(_value "${LIST_${_name}}")
    if("${_value}" STREQUAL "")
      set(_display_${_name} "none")
    else()
      string(JOIN ", " _display_${_name} ${_value})
    endif()
  endforeach()

  get_property(_languages GLOBAL PROPERTY BESA_ENABLED_LANGUAGES)
  if(NOT _languages)
    set(_display_languages "none")
  else()
    string(JOIN ", " _display_languages ${_languages})
  endif()

  if(BUILD_TESTING)
    set(_build_testing ON)
  else()
    set(_build_testing OFF)
  endif()

  string(TOLOWER "${PROJECT_NAME}" _besa_project_name_lower)
  message(STATUS "${_besa_project_name_lower} configuration:")
  message(STATUS "  Features      : ${_display_FEATURES}")
  message(STATUS "  Devtools      : ${_display_DEVTOOLS}")
  message(STATUS "  Warning policy: ${_display_WARNINGS}")
  message(STATUS "  Test modes    : ${_display_TEST_MODES}")
  message(STATUS "  Languages     : ${_display_languages}")
  message(STATUS "  Build testing : ${_build_testing}")
  message(STATUS "  Release type  : ${RELEASE_TYPE}")
  message(STATUS "  Release rev.  : ${RELEASE_REVISION}")
  message(STATUS "  Package builder: ${PKGBUILDER_ID}")
  message(STATUS "  Package rev.   : ${PKGBUILDER_REVISION}")
  message(STATUS "  Version       : ${PROJECT_SEMVER}")
endfunction()

# Finish the declaration/configuration phase.
#
# Ordering is intentional:
#   1. resolve project features, BESA devtools, project test modes, and BESA warning policies;
#   2. reject duplicate/unknown selections in every configuration family;
#   3. run project-provided feature/devtool/test-mode constraints;
#   4. publish the valid resolved configuration;
#   5. enable languages implied by toolchain-* features;
#   6. activate compiler-dependent devtools and resolve release/version policy;
#   7. freeze configuration and allow dependency/directory/target/test declarations.
macro(besa_configure_complete)
  cmake_parse_arguments(ARG "" "" "" ${ARGN})
  _besa_require_no_unparsed("besa_configure_complete" "${ARG_UNPARSED_ARGUMENTS}")
  _besa_require_config_open("besa_configure_complete")

  _besa_resolve_features(_enabled_features)
  _besa_devtools_resolve(_enabled_devtools)
  _besa_resolve_test_modes(_enabled_test_modes)
  _besa_warnings_resolve(_enabled_warnings)

  # Constraints see fully resolved sets, including defaults and explicit overrides, but run before
  # language probing or instrumentation target creation.  Invalid configurations therefore fail
  # before compiler/tool side effects occur.
  _besa_run_feature_constraints("${_enabled_features}")
  _besa_run_devtool_constraints("${_enabled_devtools}")
  _besa_run_test_mode_constraints("${_enabled_test_modes}")

  set_property(GLOBAL PROPERTY BESA_ENABLED_FEATURES "${_enabled_features}")
  set(BESA_ENABLED_FEATURES "${_enabled_features}" CACHE INTERNAL "Resolved enabled BESA features")
  _besa_publish_feature_booleans("${_enabled_features}")
  _besa_publish_test_modes("${_enabled_test_modes}")

  _besa_enable_toolchain_languages(_enabled_features)
  _besa_devtools_activate()
  _besa_version_resolve()

  _besa_configuration_summary(
    "${_enabled_features}"
    "${_enabled_devtools}"
    "${_enabled_test_modes}"
    "${_enabled_warnings}"
  )

  set_property(GLOBAL PROPERTY BESA_CONFIGURATION_COMPLETE TRUE)

  # Packaging and project-wide instrumentation need the complete target/dependency graph, so they
  # are finalized only after all project CMakeLists.txt files have been processed.
  cmake_language(EVAL CODE
    "cmake_language(DEFER DIRECTORY [[${PROJECT_SOURCE_DIR}]] CALL _besa_project_finalize)"
  )
endmacro()
