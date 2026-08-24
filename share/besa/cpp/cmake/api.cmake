# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
include_guard(GLOBAL)
include("${CMAKE_CURRENT_LIST_DIR}/internal.cmake")

set(_besa_api_valid_classifications PUBLIC NONE)

function(_besa_api_classification_parse FUNCTION_NAME API_VALUE DEFAULT_VALUE OUTPUT_API)
  if("${API_VALUE}" STREQUAL "")
    set(_api "${DEFAULT_VALUE}")
  else()
    string(TOUPPER "${API_VALUE}" _api)
  endif()

  if(NOT _api IN_LIST _besa_api_valid_classifications)
    _besa_fatal("${FUNCTION_NAME}" "API must be PUBLIC or NONE; got '${API_VALUE}'")
  endif()

  string(TOLOWER "${_api}" _api)
  set("${OUTPUT_API}" "${_api}" PARENT_SCOPE)
endfunction()

function(_besa_api_register)
  cmake_parse_arguments(
    ARG
    "SELECTED"
    "KIND;NAME;PATH;BASE;LANGUAGE;API"
    ""
    ${ARGN}
  )
  _besa_require_no_unparsed("_besa_api_register" "${ARG_UNPARSED_ARGUMENTS}")

  get_property(_count GLOBAL PROPERTY BESA_API_REGISTRATION_COUNT)
  if("${_count}" STREQUAL "")
    set(_count 0)
  endif()

  math(EXPR _next "${_count} + 1")
  set_property(GLOBAL PROPERTY BESA_API_REGISTRATION_COUNT "${_next}")
  foreach(_field IN ITEMS KIND NAME PATH BASE LANGUAGE API SELECTED)
    if(_field STREQUAL "SELECTED")
      if(ARG_SELECTED)
        set(_value TRUE)
      else()
        set(_value FALSE)
      endif()
    else()
      set(_value "${ARG_${_field}}")
    endif()
    set_property(GLOBAL PROPERTY "BESA_API_REGISTRATION_${_count}_${_field}" "${_value}")
  endforeach()
endfunction()

# An API profile is a compilation context, not a complete project configuration. FEATURES are
# mandatory prerequisites for that context; ordinary project features remain an independent
# configuration axis. PREDEFINED contains parser-only compiler definitions needed for API discovery.
function(besa_api_profile_add)
  _besa_require_config_open("besa_api_profile_add")
  cmake_parse_arguments(ARG "" "NAME" "FEATURES;PREDEFINED" ${ARGN})
  _besa_require_no_unparsed("besa_api_profile_add" "${ARG_UNPARSED_ARGUMENTS}")
  _besa_require_value("besa_api_profile_add" "NAME" "${ARG_NAME}")

  if(NOT ARG_NAME MATCHES "^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    _besa_fatal(
      "besa_api_profile_add"
      "NAME '${ARG_NAME}' must use letters, digits, '.', '_', or '-'"
    )
  endif()

  get_property(_names GLOBAL PROPERTY BESA_API_PROFILE_NAMES)
  if("${ARG_NAME}" IN_LIST _names)
    _besa_fatal("besa_api_profile_add" "profile '${ARG_NAME}' is already registered")
  endif()

  get_property(_declared GLOBAL PROPERTY BESA_DECLARED_FEATURES)
  foreach(_feature IN LISTS ARG_FEATURES)
    if("${_feature}" MATCHES "^~")
      _besa_fatal(
        "besa_api_profile_add"
        "profile features are mandatory positive prerequisites; '${_feature}' must not use '~'"
      )
    endif()
    if(NOT "${_feature}" IN_LIST _declared)
      _besa_fatal("besa_api_profile_add" "unknown feature '${_feature}'")
    endif()
  endforeach()

  list(REMOVE_DUPLICATES ARG_FEATURES)
  list(REMOVE_DUPLICATES ARG_PREDEFINED)
  set_property(GLOBAL APPEND PROPERTY BESA_API_PROFILE_NAMES "${ARG_NAME}")
  set_property(GLOBAL PROPERTY "BESA_API_PROFILE_${ARG_NAME}_FEATURES" "${ARG_FEATURES}")
  set_property(GLOBAL PROPERTY "BESA_API_PROFILE_${ARG_NAME}_PREDEFINED" "${ARG_PREDEFINED}")
endfunction()

function(_besa_api_profile_get NAME OUTPUT_FEATURES OUTPUT_PREDEFINED)
  get_property(_profiles GLOBAL PROPERTY BESA_API_PROFILE_NAMES)
  if(NOT "${NAME}" IN_LIST _profiles)
    _besa_fatal("BESA_API_PROFILE" "unknown API profile '${NAME}'. Registered profiles: ${_profiles}")
  endif()
  get_property(_features GLOBAL PROPERTY "BESA_API_PROFILE_${NAME}_FEATURES")
  get_property(_predefined GLOBAL PROPERTY "BESA_API_PROFILE_${NAME}_PREDEFINED")
  set("${OUTPUT_FEATURES}" "${_features}" PARENT_SCOPE)
  set("${OUTPUT_PREDEFINED}" "${_predefined}" PARENT_SCOPE)
endfunction()

function(_besa_api_profiles_validate)
  # Profile declarations are partial compilation contexts. Full feature validity is checked for
  # concrete configurations, not by pretending a profile alone is a complete project build.
endfunction()

function(_besa_api_json_escape INPUT OUTPUT_VARIABLE)
  set(_value "${INPUT}")
  string(REPLACE "\\" "\\\\" _value "${_value}")
  string(REPLACE "\"" "\\\"" _value "${_value}")
  string(REPLACE "\n" "\\n" _value "${_value}")
  string(REPLACE "\r" "\\r" _value "${_value}")
  string(REPLACE "\t" "\\t" _value "${_value}")
  set("${OUTPUT_VARIABLE}" "${_value}" PARENT_SCOPE)
endfunction()

function(_besa_api_json_string INPUT OUTPUT_VARIABLE)
  _besa_api_json_escape("${INPUT}" _escaped)
  set("${OUTPUT_VARIABLE}" "\"${_escaped}\"" PARENT_SCOPE)
endfunction()

function(_besa_api_json_array OUTPUT_VARIABLE)
  set(_items)
  foreach(_value IN LISTS ARGN)
    _besa_api_json_string("${_value}" _quoted)
    list(APPEND _items "${_quoted}")
  endforeach()
  if(_items)
    string(JOIN ", " _body ${_items})
  else()
    set(_body "")
  endif()
  set("${OUTPUT_VARIABLE}" "[${_body}]" PARENT_SCOPE)
endfunction()

function(_besa_api_manifest_finalize)
  set(_directory "${PROJECT_BINARY_DIR}/besa")
  set(_manifest "${_directory}/api-manifest.json")
  file(MAKE_DIRECTORY "${_directory}")

  _besa_api_json_string("${PROJECT_NAME}" _project_json)
  if(DEFINED BESA_PROJECT_MODEL AND EXISTS "${BESA_PROJECT_MODEL}")
    file(READ "${BESA_PROJECT_MODEL}" _project_model_json)
    string(STRIP "${_project_model_json}" _project_model_json)
  else()
    set(_project_model_json null)
  endif()
  if(DEFINED BESA_API_CONFIGURATION_SPACE AND EXISTS "${BESA_API_CONFIGURATION_SPACE}")
    file(READ "${BESA_API_CONFIGURATION_SPACE}" _configuration_space_json)
    string(STRIP "${_configuration_space_json}" _configuration_space_json)
  else()
    set(_configuration_space_json null)
  endif()
  get_property(_declared GLOBAL PROPERTY BESA_DECLARED_FEATURES)
  get_property(_enabled GLOBAL PROPERTY BESA_ENABLED_FEATURES)
  _besa_api_json_array(_declared_json ${_declared})
  _besa_api_json_array(_enabled_json ${_enabled})
  if(DEFINED BESA_API_PROFILE AND NOT "${BESA_API_PROFILE}" STREQUAL "")
    _besa_api_json_string("${BESA_API_PROFILE}" _active_profile_json)
  else()
    set(_active_profile_json null)
  endif()

  set(_profile_objects)
  get_property(_profiles GLOBAL PROPERTY BESA_API_PROFILE_NAMES)
  foreach(_profile IN LISTS _profiles)
    get_property(_features GLOBAL PROPERTY "BESA_API_PROFILE_${_profile}_FEATURES")
    get_property(_predefined GLOBAL PROPERTY "BESA_API_PROFILE_${_profile}_PREDEFINED")
    _besa_api_json_string("${_profile}" _name_json)
    _besa_api_json_array(_features_json ${_features})
    _besa_api_json_array(_predefined_json ${_predefined})
    list(APPEND _profile_objects
      "    {\"name\": ${_name_json}, \"features\": ${_features_json}, \"predefined\": ${_predefined_json}}"
    )
  endforeach()
  if(_profile_objects)
    string(JOIN ",\n" _profiles_json ${_profile_objects})
  else()
    set(_profiles_json "")
  endif()

  set(_registration_objects)
  get_property(_count GLOBAL PROPERTY BESA_API_REGISTRATION_COUNT)
  if("${_count}" STREQUAL "")
    set(_count 0)
  endif()
  if(_count GREATER 0)
    math(EXPR _last "${_count} - 1")
    foreach(_index RANGE 0 ${_last})
      foreach(_field IN ITEMS KIND NAME PATH BASE LANGUAGE API SELECTED)
        get_property(_${_field} GLOBAL PROPERTY "BESA_API_REGISTRATION_${_index}_${_field}")
      endforeach()

      _besa_api_json_string("${_KIND}" _kind_json)
      _besa_api_json_string("${_NAME}" _name_json)
      _besa_api_json_string("${_PATH}" _path_json)
      _besa_api_json_string("${_BASE}" _base_json)
      _besa_api_json_string("${_API}" _api_json)
      if("${_LANGUAGE}" STREQUAL "")
        set(_language_json null)
      else()
        _besa_api_json_string("${_LANGUAGE}" _language_json)
      endif()
      if(_SELECTED)
        set(_selected_json true)
      else()
        set(_selected_json false)
      endif()

      list(APPEND _registration_objects
        "    {\"kind\": ${_kind_json}, \"name\": ${_name_json}, \"path\": ${_path_json}, \"base\": ${_base_json}, \"language\": ${_language_json}, \"api\": ${_api_json}, \"selected\": ${_selected_json}}"
      )
    endforeach()
  endif()
  if(_registration_objects)
    string(JOIN ",\n" _registrations_json ${_registration_objects})
  else()
    set(_registrations_json "")
  endif()

  file(WRITE "${_manifest}"
    "{\n"
    "  \"schema_version\": 1,\n"
    "  \"project\": ${_project_json},\n"
    "  \"active_profile\": ${_active_profile_json},\n"
    "  \"declared_features\": ${_declared_json},\n"
    "  \"active_features\": ${_enabled_json},\n"
    "  \"project_model\": ${_project_model_json},\n"
    "  \"api_configuration_space\": ${_configuration_space_json},\n"
    "  \"profiles\": [\n${_profiles_json}\n  ],\n"
    "  \"registrations\": [\n${_registrations_json}\n  ]\n"
    "}\n"
  )
  set(BESA_API_MANIFEST "${_manifest}" CACHE INTERNAL "BESA API manifest")
endfunction()
