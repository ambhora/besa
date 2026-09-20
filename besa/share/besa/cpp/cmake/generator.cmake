# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
include_guard(GLOBAL)
include("${CMAKE_CURRENT_LIST_DIR}/model.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/generated.cmake")

# Run a portable Python generator. The callback receives (context: dict, output: Path). The output
# prefix is constrained to bin/, include/, lib/, and optional mod/. Path-typed context values are
# content dependencies and therefore participate in cache invalidation.
function(besa_generator_run)
  cmake_parse_arguments(ARG "" "NAME;CALLBACK;CONTEXT;API;OUTPUT_VARIABLE" "" ${ARGN})
  _besa_require_no_unparsed("besa_generator_run" "${ARG_UNPARSED_ARGUMENTS}")
  _besa_require_value("besa_generator_run" "NAME" "${ARG_NAME}")
  _besa_require_value("besa_generator_run" "CALLBACK" "${ARG_CALLBACK}")
  _besa_require_value("besa_generator_run" "CONTEXT" "${ARG_CONTEXT}")

  if(NOT EXISTS "${ARG_CONTEXT}")
    _besa_fatal("besa_generator_run" "CONTEXT does not exist: ${ARG_CONTEXT}")
  endif()
  if(NOT DEFINED BESA_CODEGEN_DIRECTORY OR "${BESA_CODEGEN_DIRECTORY}" STREQUAL "")
    besa_workspace_initialize()
  endif()
  _besa_model_python(_python)
  set(_output "${BESA_CODEGEN_DIRECTORY}/${ARG_NAME}")
  set(_cache "${BESA_CONFIGURE_CACHE_DIRECTORY}/generators/${ARG_NAME}.json")
  execute_process(
    COMMAND
      "${_python}" "${CMAKE_CURRENT_LIST_DIR}/python/generator.py"
      --callback "${ARG_CALLBACK}"
      --context "${ARG_CONTEXT}"
      --project-root "${PROJECT_SOURCE_DIR}"
      --output "${_output}"
      --cache "${_cache}"
    RESULT_VARIABLE _result
    ERROR_VARIABLE _stderr
  )
  if(NOT _result EQUAL 0)
    _besa_fatal("besa_generator_run" "generator '${ARG_NAME}' failed:\n${_stderr}")
  endif()

  besa_generated_prefix_add(NAME "${ARG_NAME}" API "${ARG_API}" OUTPUT_VARIABLE _prefix)
  if(ARG_OUTPUT_VARIABLE)
    set("${ARG_OUTPUT_VARIABLE}" "${_prefix}" PARENT_SCOPE)
  endif()
endfunction()
