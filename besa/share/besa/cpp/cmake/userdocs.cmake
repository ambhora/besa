# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Documentation helpers for C and C++ projects.
#
# ProperDocs owns project documentation. cpdoc owns the standalone, versioned API reference. The
# installed properdocs-cpdoc plugin joins both trees for normal ProperDocs build/serve workflows.

include_guard(GLOBAL)
include("${CMAKE_CURRENT_LIST_DIR}/internal.cmake")

# Register explicit cpdoc targets for API-only development and CI.
function(besa_add_cpdoc_docs)
  _besa_require_config_complete("besa_add_cpdoc_docs")
  include(GNUInstallDirs)

  cmake_parse_arguments(
    ARG
    "NO_INSTALL"
    "NAME;CONFIG;OUTPUT_DIRECTORY;VERSIONS_NAME;VERSIONS_OUTPUT_DIRECTORY;INSTALL_DIRECTORY;VERSIONS_INSTALL_DIRECTORY"
    ""
    ${ARGN}
  )
  _besa_require_no_unparsed("besa_add_cpdoc_docs" "${ARG_UNPARSED_ARGUMENTS}")
  _besa_require_value("besa_add_cpdoc_docs" "NAME" "${ARG_NAME}")
  _besa_require_value("besa_add_cpdoc_docs" "CONFIG" "${ARG_CONFIG}")

  if(NOT ARG_OUTPUT_DIRECTORY)
    set(ARG_OUTPUT_DIRECTORY "${BESA_DOCS_DIRECTORY}/api/current")
  endif()
  if(NOT ARG_VERSIONS_NAME)
    set(ARG_VERSIONS_NAME "${ARG_NAME}.versions")
  endif()
  if(NOT ARG_VERSIONS_OUTPUT_DIRECTORY)
    set(ARG_VERSIONS_OUTPUT_DIRECTORY "${BESA_DOCS_DIRECTORY}/api/versions")
  endif()

  get_filename_component(
    _besa_cpdoc_config
    "${ARG_CONFIG}"
    ABSOLUTE
    BASE_DIR "${PROJECT_SOURCE_DIR}"
  )
  if(NOT EXISTS "${_besa_cpdoc_config}")
    message(FATAL_ERROR "besa_add_cpdoc_docs: CONFIG does not exist: ${_besa_cpdoc_config}")
  endif()

  find_program(_besa_cpdoc NAMES cpdoc REQUIRED)
  set(_besa_cpdoc_work "${BESA_DOCS_DIRECTORY}/work/cpdoc")

  set(BESA_API_VARIANTS "" CACHE STRING "cpdoc API variants to extract; empty means all variants")
  set(_besa_api_variant_arguments "")
  foreach(_variant IN LISTS BESA_API_VARIANTS)
    if(NOT _variant STREQUAL "")
      list(APPEND _besa_api_variant_arguments --variant "${_variant}")
    endif()
  endforeach()

  add_custom_target(
    "${ARG_NAME}"
    COMMAND "${CMAKE_COMMAND}" -E rm -rf "${ARG_OUTPUT_DIRECTORY}"
    COMMAND
      "${_besa_cpdoc}" --config "${_besa_cpdoc_config}" build
      --output-directory "${ARG_OUTPUT_DIRECTORY}"
      --work-directory "${_besa_cpdoc_work}/current"
      --version main
      ${_besa_api_variant_arguments}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMENT "Generating semantic API documentation with cpdoc"
    VERBATIM
  )
  if(TARGET besa.generated)
    add_dependencies("${ARG_NAME}" besa.generated)
  endif()

  add_custom_target(
    "${ARG_VERSIONS_NAME}"
    COMMAND "${CMAKE_COMMAND}" -E rm -rf "${ARG_VERSIONS_OUTPUT_DIRECTORY}"
    COMMAND
      "${_besa_cpdoc}" --config "${_besa_cpdoc_config}" versions
      --output-directory "${ARG_VERSIONS_OUTPUT_DIRECTORY}"
      --work-directory "${_besa_cpdoc_work}/versions"
      ${_besa_api_variant_arguments}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMENT "Generating versioned semantic API documentation with cpdoc"
    VERBATIM
  )

  if(NOT ARG_NO_INSTALL)
    if(NOT ARG_INSTALL_DIRECTORY)
      set(ARG_INSTALL_DIRECTORY "${CMAKE_INSTALL_DOCDIR}/api/current")
    endif()
    if(NOT ARG_VERSIONS_INSTALL_DIRECTORY)
      set(ARG_VERSIONS_INSTALL_DIRECTORY "${CMAKE_INSTALL_DOCDIR}/api")
    endif()
    install(DIRECTORY "${ARG_OUTPUT_DIRECTORY}/" DESTINATION "${ARG_INSTALL_DIRECTORY}" OPTIONAL)
    install(
      DIRECTORY "${ARG_VERSIONS_OUTPUT_DIRECTORY}/"
      DESTINATION "${ARG_VERSIONS_INSTALL_DIRECTORY}"
      OPTIONAL
    )
  endif()
endfunction()

# Register the complete user-documentation site. ProperDocs invokes properdocs-cpdoc, so there is no
# second site build and no assembly phase. NAME is the deployable site target; NAME.api and
# NAME.api.versions remain convenient explicit cpdoc targets.
function(besa_add_user_docs)
  _besa_require_config_complete("besa_add_user_docs")
  include(GNUInstallDirs)

  cmake_parse_arguments(
    ARG
    ""
    "NAME;PROPERDOCS_CONFIG;CPDOC_CONFIG;OUTPUT_DIRECTORY;INSTALL_DIRECTORY"
    ""
    ${ARGN}
  )
  _besa_require_no_unparsed("besa_add_user_docs" "${ARG_UNPARSED_ARGUMENTS}")
  _besa_require_value("besa_add_user_docs" "NAME" "${ARG_NAME}")
  _besa_require_value("besa_add_user_docs" "PROPERDOCS_CONFIG" "${ARG_PROPERDOCS_CONFIG}")
  _besa_require_value("besa_add_user_docs" "CPDOC_CONFIG" "${ARG_CPDOC_CONFIG}")

  if(NOT ARG_OUTPUT_DIRECTORY)
    set(ARG_OUTPUT_DIRECTORY "${BESA_DOCS_DIRECTORY}/site")
  endif()
  if(NOT ARG_INSTALL_DIRECTORY)
    set(ARG_INSTALL_DIRECTORY "${CMAKE_INSTALL_DOCDIR}")
  endif()

  get_filename_component(
    _besa_properdocs_config
    "${ARG_PROPERDOCS_CONFIG}"
    ABSOLUTE
    BASE_DIR "${PROJECT_SOURCE_DIR}"
  )
  if(NOT EXISTS "${_besa_properdocs_config}")
    message(FATAL_ERROR "besa_add_user_docs: PROPERDOCS_CONFIG does not exist: ${_besa_properdocs_config}")
  endif()

  find_program(_besa_properdocs NAMES properdocs REQUIRED)

  besa_add_cpdoc_docs(
    NAME "${ARG_NAME}.api"
    CONFIG "${ARG_CPDOC_CONFIG}"
    OUTPUT_DIRECTORY "${BESA_DOCS_DIRECTORY}/api/current"
    VERSIONS_OUTPUT_DIRECTORY "${BESA_DOCS_DIRECTORY}/api/versions"
    NO_INSTALL
  )

  add_custom_target(
    "${ARG_NAME}"
    COMMAND
      "${_besa_properdocs}" build
      --config-file "${_besa_properdocs_config}"
      --site-dir "${ARG_OUTPUT_DIRECTORY}"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMENT "Generating the ProperDocs site with the cpdoc API reference"
    VERBATIM
  )

  install(
    DIRECTORY "${ARG_OUTPUT_DIRECTORY}/"
    DESTINATION "${ARG_INSTALL_DIRECTORY}"
    OPTIONAL
  )
endfunction()
