# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
include_guard(GLOBAL)
set(_BESA_MODEL_MODULE_DIR "${CMAKE_CURRENT_LIST_DIR}")

function(_besa_model_python OUTPUT_VARIABLE)
  if(DEFINED BESA_MODEL_PYTHON AND NOT "${BESA_MODEL_PYTHON}" STREQUAL "")
    set("${OUTPUT_VARIABLE}" "${BESA_MODEL_PYTHON}" PARENT_SCOPE)
    return()
  endif()
  find_program(_python NAMES python3 python REQUIRED)
  set(BESA_MODEL_PYTHON "${_python}" CACHE FILEPATH "Python interpreter used by the BESA model")
  set("${OUTPUT_VARIABLE}" "${_python}" PARENT_SCOPE)
endfunction()

function(_besa_model_run)
  cmake_parse_arguments(ARG "" "FILE;OUTPUT" "ARGUMENTS" ${ARGN})
  if(NOT ARG_FILE OR NOT ARG_OUTPUT)
    message(FATAL_ERROR "_besa_model_run: FILE and OUTPUT are required")
  endif()
  _besa_model_python(_python)
  execute_process(
    COMMAND
      "${_python}" "${_BESA_MODEL_MODULE_DIR}/python/model.py"
      ${ARG_ARGUMENTS}
      --file "${ARG_FILE}"
      --output "${ARG_OUTPUT}"
    RESULT_VARIABLE _result
    OUTPUT_VARIABLE _stdout
    ERROR_VARIABLE _stderr
  )
  if(NOT _result EQUAL 0)
    message(FATAL_ERROR "BESA model processing failed:\n${_stderr}")
  endif()
endfunction()

# Read only project identity. This function is deliberately usable before project().
function(besa_model_bootstrap)
  cmake_parse_arguments(ARG "" "FILE" "" ${ARGN})
  if(NOT ARG_FILE)
    message(FATAL_ERROR "besa_model_bootstrap: FILE is required")
  endif()
  get_filename_component(_file "${ARG_FILE}" ABSOLUTE BASE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
  set(_output "${CMAKE_BINARY_DIR}/besa/model-bootstrap.cmake")
  file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}/besa")
  _besa_model_run(FILE "${_file}" OUTPUT "${_output}" ARGUMENTS bootstrap)
  include("${_output}")
  set(BESA_MODEL_PROJECT_NAME "${BESA_MODEL_PROJECT_NAME}" PARENT_SCOPE)
  set(BESA_MODEL_PROJECT_VERSION "${BESA_MODEL_PROJECT_VERSION}" PARENT_SCOPE)
endfunction()

function(_besa_model_condition_evaluate JSON ENABLED_FEATURES OUTPUT_VARIABLE)
  string(JSON _type TYPE "${JSON}")
  if(NOT _type STREQUAL "OBJECT")
    message(FATAL_ERROR "BESA model condition must be a JSON object")
  endif()
  string(JSON _length LENGTH "${JSON}")
  if(NOT _length EQUAL 1)
    message(FATAL_ERROR "BESA model condition must contain exactly one operator")
  endif()
  string(JSON _operator MEMBER "${JSON}" 0)
  if(_operator STREQUAL "all" OR _operator STREQUAL "any")
    string(JSON _count LENGTH "${JSON}" "${_operator}")
    if(_operator STREQUAL "all")
      set(_result TRUE)
    else()
      set(_result FALSE)
    endif()
    if(_count GREATER 0)
      math(EXPR _last "${_count} - 1")
      foreach(_index RANGE 0 ${_last})
        string(JSON _item_type TYPE "${JSON}" "${_operator}" ${_index})
        if(_item_type STREQUAL "STRING")
          string(JSON _feature GET "${JSON}" "${_operator}" ${_index})
          if("${_feature}" IN_LIST ENABLED_FEATURES)
            set(_matches TRUE)
          else()
            set(_matches FALSE)
          endif()
        else()
          string(JSON _child GET "${JSON}" "${_operator}" ${_index})
          _besa_model_condition_evaluate("${_child}" "${ENABLED_FEATURES}" _matches)
        endif()
        if(_operator STREQUAL "all" AND NOT _matches)
          set(_result FALSE)
          break()
        elseif(_operator STREQUAL "any" AND _matches)
          set(_result TRUE)
          break()
        endif()
      endforeach()
    endif()
  elseif(_operator STREQUAL "not")
    string(JSON _item_type TYPE "${JSON}" not)
    if(_item_type STREQUAL "STRING")
      string(JSON _feature GET "${JSON}" not)
      if("${_feature}" IN_LIST ENABLED_FEATURES)
        set(_result FALSE)
      else()
        set(_result TRUE)
      endif()
    else()
      string(JSON _child GET "${JSON}" not)
      _besa_model_condition_evaluate("${_child}" "${ENABLED_FEATURES}" _child_result)
      if(_child_result)
        set(_result FALSE)
      else()
        set(_result TRUE)
      endif()
    endif()
  else()
    message(FATAL_ERROR "Unknown BESA model condition operator '${_operator}'")
  endif()
  set("${OUTPUT_VARIABLE}" "${_result}" PARENT_SCOPE)
endfunction()

function(_besa_model_constraint_evaluate DOMAIN ACCEPTED ENABLED_FEATURES OUTPUT_VARIABLE)
  set(_key "")
  foreach(_feature IN LISTS DOMAIN)
    if("${_feature}" IN_LIST ENABLED_FEATURES)
      string(APPEND _key "1")
    else()
      string(APPEND _key "0")
    endif()
  endforeach()
  if("${_key}" IN_LIST ACCEPTED)
    set(_valid TRUE)
  else()
    set(_valid FALSE)
  endif()
  set("${OUTPUT_VARIABLE}" "${_valid}" PARENT_SCOPE)
endfunction()

function(besa_workspace_initialize)
  if(NOT DEFINED BESA_WORKSPACE OR "${BESA_WORKSPACE}" STREQUAL "")
    get_filename_component(_workspace "${PROJECT_BINARY_DIR}" DIRECTORY)
    set(BESA_WORKSPACE "${_workspace}" CACHE PATH "BESA workspace root")
  endif()
  get_filename_component(BESA_WORKSPACE "${BESA_WORKSPACE}" ABSOLUTE)
  set(BESA_BUILD_DIRECTORY "${PROJECT_BINARY_DIR}" CACHE INTERNAL "BESA build directory")
  set(BESA_CODEGEN_DIRECTORY "${BESA_WORKSPACE}/codegen" CACHE INTERNAL "BESA code-generation directory")
  set(BESA_DOCS_DIRECTORY "${BESA_WORKSPACE}/docs" CACHE INTERNAL "BESA documentation directory")
  set(BESA_CONFIGURE_CACHE_DIRECTORY "${BESA_WORKSPACE}/configure_cache" CACHE INTERNAL "BESA configure cache")
  file(MAKE_DIRECTORY
    "${BESA_CODEGEN_DIRECTORY}"
    "${BESA_DOCS_DIRECTORY}"
    "${BESA_CONFIGURE_CACHE_DIRECTORY}"
  )
endfunction()

macro(besa_model_realize)
  cmake_parse_arguments(ARG "" "FILE" "" ${ARGN})
  if(NOT ARG_FILE)
    message(FATAL_ERROR "besa_model_realize: FILE is required")
  endif()
  get_filename_component(_file "${ARG_FILE}" ABSOLUTE BASE_DIR "${PROJECT_SOURCE_DIR}")
  besa_workspace_initialize()

  if(BUILD_TESTING)
    set_property(GLOBAL APPEND PROPERTY BESA_BACKEND_FEATURES build-testing)
  endif()

  set(_directory "${BESA_CONFIGURE_CACHE_DIRECTORY}/model")
  file(MAKE_DIRECTORY "${_directory}")
  set(_cmake "${_directory}/project-model.cmake")
  set(_normalized "${_directory}/project-model.json")
  set(_space "${BESA_CONFIGURE_CACHE_DIRECTORY}/api/configurations.json")
  file(MAKE_DIRECTORY "${BESA_CONFIGURE_CACHE_DIRECTORY}/api")

  _besa_model_python(_python)
  execute_process(
    COMMAND
      "${_python}" "${_BESA_MODEL_MODULE_DIR}/python/model.py" emit
      --file "${_file}"
      --output "${_cmake}"
      --normalized "${_normalized}"
      --configuration-space "${_space}"
      --cache "${BESA_CONFIGURE_CACHE_DIRECTORY}"
    RESULT_VARIABLE _result
    ERROR_VARIABLE _stderr
  )
  if(NOT _result EQUAL 0)
    message(FATAL_ERROR "BESA model processing failed:\n${_stderr}")
  endif()

  set(BESA_PROJECT_MODEL "${_normalized}" CACHE INTERNAL "Normalized BESA project model")
  set(BESA_API_CONFIGURATION_SPACE "${_space}" CACHE INTERNAL "Derived API configuration space")
  include("${_cmake}")
endmacro()
