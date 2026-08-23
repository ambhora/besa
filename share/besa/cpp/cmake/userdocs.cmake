# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Documentation helpers for C and C++ projects.
#
# BESA separates the user-facing information architecture from generated API reference:
#
#   ProperDocs                         -> main documentation site
#   Doxygen -> XML -> Breathe -> Exhale -> Sphinx -> versioned API reference
#
# The high-level `besa_add_user_docs()` helper assembles both trees into one publication artifact.
# ProperDocs always owns the site root and the API reference is mounted below a configured path such
# as `reference/api/<version>/`.  The lower-level Doxygen and Sphinx helpers remain available for
# projects which need only one layer of this pipeline.

include_guard(GLOBAL)
include("${CMAKE_CURRENT_LIST_DIR}/internal.cmake")

function(besa_add_doxygen)
  _besa_require_config_complete("besa_add_doxygen")
  cmake_parse_arguments(ARG "" "NAME;DOXYFILE;OUTPUT_DIRECTORY" "" ${ARGN})
  _besa_require_no_unparsed("besa_add_doxygen" "${ARG_UNPARSED_ARGUMENTS}")
  _besa_require_value("besa_add_doxygen" "NAME" "${ARG_NAME}")
  _besa_require_value("besa_add_doxygen" "DOXYFILE" "${ARG_DOXYFILE}")
  if(NOT ARG_OUTPUT_DIRECTORY)
    set(ARG_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/doc")
  endif()

  find_package(Doxygen REQUIRED COMPONENTS dot)
  file(MAKE_DIRECTORY "${ARG_OUTPUT_DIRECTORY}")
  set(DOXYGEN_OUTPUT_DIRECTORY "${ARG_OUTPUT_DIRECTORY}")
  configure_file("${ARG_DOXYFILE}" "${ARG_OUTPUT_DIRECTORY}/Doxyfile" @ONLY)
  add_custom_target(
    "${ARG_NAME}"
    COMMAND Doxygen::doxygen "${ARG_OUTPUT_DIRECTORY}/Doxyfile"
    WORKING_DIRECTORY "${ARG_OUTPUT_DIRECTORY}"
    COMMENT "Generating Doxygen documentation"
    VERBATIM
  )
  if(TARGET besa.generated)
    add_dependencies("${ARG_NAME}" besa.generated)
  endif()
endfunction()

# Register single-checkout and multiversion Sphinx API-reference targets backed by Doxygen XML,
# Breathe, and Exhale.  This helper intentionally knows nothing about the main documentation site; the higher-
# level besa_add_user_docs() helper decides where the API tree is mounted.
#
# NAME
#   Name of the ordinary, single-checkout Sphinx target.
#
# SOURCE_DIRECTORY
#   Sphinx source directory containing conf.py and Doxyfile.in. The project CMake configuration
#   materializes the template into <binary>/api-docs/Doxyfile for the exact checkout.
#
# OUTPUT_DIRECTORY
#   HTML output directory for the current checkout. Defaults to <binary>/doc/api/current.
#
# MULTIVERSION_NAME
#   Name of the sphinx-multiversion target. Defaults to <NAME>.multiversion.
#
# MULTIVERSION_OUTPUT_DIRECTORY
#   Root output directory for all selected Git refs. Defaults to <binary>/doc/api/multiversion.
#   The root contains versions.json plus one Sphinx tree per selected ref; it deliberately does not
#   contain a publication-root index.html because ProperDocs owns that page in an assembled site.
#
# MULTIVERSION_DEFAULT_VERSION
#   Preferred/default API ref recorded in versions.json. Defaults to `main`.
#
# DOXYGEN_OUTPUT_DIRECTORY
#   Base directory used by conf.py for per-checkout Doxygen XML trees. Defaults to
#   <binary>/doc/doxygen.
#
# SITE_ROOT_DEPTH
#   Number of directory levels from an API-version root back to the final documentation-site root.
#   It is passed to Sphinx so the generated sidebar can provide a deployment-prefix-independent link
#   back to ProperDocs. Defaults to 3, matching reference/api/<version>/.
#
# NO_INSTALL
#   Suppress this lower-level helper's standalone install rules. besa_add_user_docs() uses this
#   because it installs only the fully assembled ProperDocs + API site.
function(besa_add_sphinx_breathe_docs)
  _besa_require_config_complete("besa_add_sphinx_breathe_docs")
  include(GNUInstallDirs)

  cmake_parse_arguments(
    ARG
    "NO_INSTALL"
    "NAME;SOURCE_DIRECTORY;OUTPUT_DIRECTORY;MULTIVERSION_NAME;MULTIVERSION_OUTPUT_DIRECTORY;MULTIVERSION_DEFAULT_VERSION;DOXYGEN_OUTPUT_DIRECTORY;SITE_ROOT_DEPTH;INSTALL_DIRECTORY;MULTIVERSION_INSTALL_DIRECTORY"
    ""
    ${ARGN}
  )
  _besa_require_no_unparsed("besa_add_sphinx_breathe_docs" "${ARG_UNPARSED_ARGUMENTS}")
  _besa_require_value("besa_add_sphinx_breathe_docs" "NAME" "${ARG_NAME}")
  _besa_require_value(
    "besa_add_sphinx_breathe_docs" "SOURCE_DIRECTORY" "${ARG_SOURCE_DIRECTORY}"
  )

  if(NOT ARG_OUTPUT_DIRECTORY)
    set(ARG_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/doc/api/current")
  endif()
  if(NOT ARG_MULTIVERSION_NAME)
    set(ARG_MULTIVERSION_NAME "${ARG_NAME}.multiversion")
  endif()
  if(NOT ARG_MULTIVERSION_OUTPUT_DIRECTORY)
    set(ARG_MULTIVERSION_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/doc/api/multiversion")
  endif()
  if(NOT ARG_MULTIVERSION_DEFAULT_VERSION)
    set(ARG_MULTIVERSION_DEFAULT_VERSION "main")
  endif()
  if(NOT ARG_DOXYGEN_OUTPUT_DIRECTORY)
    set(ARG_DOXYGEN_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/doc/doxygen")
  endif()
  if(NOT ARG_SITE_ROOT_DEPTH)
    set(ARG_SITE_ROOT_DEPTH 3)
  endif()
  if(NOT ARG_INSTALL_DIRECTORY)
    set(ARG_INSTALL_DIRECTORY "${CMAKE_INSTALL_DOCDIR}/api/current")
  endif()
  if(NOT ARG_MULTIVERSION_INSTALL_DIRECTORY)
    set(ARG_MULTIVERSION_INSTALL_DIRECTORY "${CMAKE_INSTALL_DOCDIR}/api")
  endif()

  get_filename_component(
    _besa_docs_source_absolute
    "${ARG_SOURCE_DIRECTORY}"
    ABSOLUTE
    BASE_DIR "${CMAKE_CURRENT_SOURCE_DIR}"
  )
  file(RELATIVE_PATH _besa_docs_source_relative "${PROJECT_SOURCE_DIR}" "${_besa_docs_source_absolute}")
  if(_besa_docs_source_relative MATCHES "^[.][.]/" OR _besa_docs_source_relative STREQUAL "..")
    message(
      FATAL_ERROR
      "besa_add_sphinx_breathe_docs: SOURCE_DIRECTORY must be inside PROJECT_SOURCE_DIR so "
      "sphinx-multiversion can resolve it in historical Git refs."
    )
  endif()

  find_package(Doxygen REQUIRED COMPONENTS dot)
  find_program(_besa_sphinx_build NAMES sphinx-build)
  find_program(_besa_sphinx_multiversion NAMES sphinx-multiversion)
  find_program(_besa_python NAMES python3 python)

  if(NOT _besa_sphinx_build)
    message(
      FATAL_ERROR
      "besa_add_sphinx_breathe_docs: sphinx-build was not found. Install Sphinx before enabling "
      "the user-docs feature."
    )
  endif()
  if(NOT _besa_sphinx_multiversion)
    message(
      FATAL_ERROR
      "besa_add_sphinx_breathe_docs: sphinx-multiversion was not found. Install "
      "sphinx-multiversion before enabling the user-docs feature."
    )
  endif()
  if(NOT _besa_python)
    message(
      FATAL_ERROR
      "besa_add_sphinx_breathe_docs: Python was not found. Python is required to resolve the "
      "BESA_API_VERSIONS selector before invoking sphinx-multiversion."
    )
  endif()

  file(MAKE_DIRECTORY "${ARG_OUTPUT_DIRECTORY}")
  file(MAKE_DIRECTORY "${ARG_MULTIVERSION_OUTPUT_DIRECTORY}")
  file(MAKE_DIRECTORY "${ARG_DOXYGEN_OUTPUT_DIRECTORY}")

  # Exhale writes generated RST below the Sphinx source tree. Never point an ordinary current-ref
  # build at the checked-in API source directly: stage that source inside the CMake build tree so
  # generated RST, doctrees, and other Sphinx working files cannot pollute PROJECT_SOURCE_DIR.
  set(_besa_current_sphinx_source "${PROJECT_BINARY_DIR}/doc/work/sphinx-current")

  # Doxygen is invoked by conf.py because sphinx-multiversion materializes historical refs itself.
  # The site-root depth is an output-layout property, not a hostname, so links back to ProperDocs
  # remain valid on GitHub project pages, custom domains, and local static hosting.
  add_custom_target(
    "${ARG_NAME}"
    COMMAND "${CMAKE_COMMAND}" -E rm -rf "${_besa_current_sphinx_source}"
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${_besa_current_sphinx_source}"
    COMMAND
      "${CMAKE_COMMAND}" -E copy_directory
      "${_besa_docs_source_absolute}" "${_besa_current_sphinx_source}"
    COMMAND
      "${CMAKE_COMMAND}" -E env
      "BESA_DOXYGEN_EXECUTABLE=$<TARGET_FILE:Doxygen::doxygen>"
      "BESA_DOXYGEN_BASE_DIRECTORY=${ARG_DOXYGEN_OUTPUT_DIRECTORY}"
      "BESA_PROJECT_SOURCE_DIRECTORY=${PROJECT_SOURCE_DIR}"
      "BESA_PROJECT_BINARY_DIRECTORY=${PROJECT_BINARY_DIR}"
      "BESA_API_PROJECT_SOURCE_DIRECTORY=${PROJECT_SOURCE_DIR}"
      "BESA_CMAKE_EXECUTABLE=${CMAKE_COMMAND}"
      "BESA_PROPERDOCS_ROOT_DEPTH=${ARG_SITE_ROOT_DEPTH}"
      "${_besa_sphinx_build}" -W --keep-going -b html
      "${_besa_current_sphinx_source}" "${ARG_OUTPUT_DIRECTORY}"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMENT "Generating structured Sphinx API documentation with Doxygen, Breathe, and Exhale"
    VERBATIM
  )
  if(TARGET besa.generated)
    add_dependencies("${ARG_NAME}" besa.generated)
  endif()

  add_custom_target(
    "${ARG_MULTIVERSION_NAME}"
    COMMAND
      "${CMAKE_COMMAND}" -E env
      "BESA_DOXYGEN_EXECUTABLE=$<TARGET_FILE:Doxygen::doxygen>"
      "BESA_DOXYGEN_BASE_DIRECTORY=${ARG_DOXYGEN_OUTPUT_DIRECTORY}"
      "BESA_PROJECT_SOURCE_DIRECTORY=${PROJECT_SOURCE_DIR}"
      "BESA_PROJECT_BINARY_DIRECTORY=${PROJECT_BINARY_DIR}"
      "BESA_CMAKE_EXECUTABLE=${CMAKE_COMMAND}"
      "BESA_PROPERDOCS_ROOT_DEPTH=${ARG_SITE_ROOT_DEPTH}"
      "${_besa_python}" "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/userdocs/multiversion.py"
      "--sphinx-multiversion" "${_besa_sphinx_multiversion}"
      "--project-root" "${PROJECT_SOURCE_DIR}"
      "--source-directory" "${_besa_docs_source_relative}"
      "--output-directory" "${ARG_MULTIVERSION_OUTPUT_DIRECTORY}"
      -- -W --keep-going
    COMMAND
      "${CMAKE_COMMAND}"
      "-DOUTPUT_DIRECTORY=${ARG_MULTIVERSION_OUTPUT_DIRECTORY}"
      "-DDEFAULT_VERSION=${ARG_MULTIVERSION_DEFAULT_VERSION}"
      -P "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/userdocs/multiversion-metadata.cmake"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMENT "Generating multiversion Sphinx API documentation from Git branches and tags"
    VERBATIM
  )
  if(TARGET besa.generated)
    add_dependencies("${ARG_MULTIVERSION_NAME}" besa.generated)
  endif()

  if(NOT ARG_NO_INSTALL)
    install(
      DIRECTORY "${ARG_OUTPUT_DIRECTORY}/"
      DESTINATION "${ARG_INSTALL_DIRECTORY}"
      OPTIONAL
    )
    install(
      DIRECTORY "${ARG_MULTIVERSION_OUTPUT_DIRECTORY}/"
      DESTINATION "${ARG_MULTIVERSION_INSTALL_DIRECTORY}"
      OPTIONAL
    )
  endif()
endfunction()

# Register the complete user-documentation site.
#
# ProperDocs owns the site root and all prose/information architecture.  Sphinx/Breathe/Exhale owns only the
# versioned API subtree.  Building NAME assembles both into one static site that can be uploaded to
# GitHub Pages without additional path rewriting.
#
# NAME
#   Final documentation target. Defaults of the derived targets are <NAME>.properdocs, <NAME>.api,
#   and <NAME>.multiversion.
#
# PROPERDOCS_CONFIG
#   Top-level properdocs.yml. ProperDocs is invoked with --site-dir, so the checked-in configuration
#   remains directly usable with `properdocs serve` while CMake keeps generated HTML in the build tree.
#
# API_SOURCE_DIRECTORY
#   Sphinx/Breathe source directory for the API reference.
#
# API_PATH
#   Relative path below the ProperDocs site root where API versions are mounted. Defaults to
#   reference/api. The ProperDocs source should provide the landing page for this path.
#
# OUTPUT_DIRECTORY
#   Final assembled site. Defaults to <binary>/doc/site.
#
# MULTIVERSION_DEFAULT_VERSION
#   Preferred API version recorded in versions.json. Defaults to main.
#
# INSTALL_DIRECTORY
#   Install destination for the complete assembled site. Defaults to CMAKE_INSTALL_DOCDIR.
function(besa_add_user_docs)
  _besa_require_config_complete("besa_add_user_docs")
  include(GNUInstallDirs)

  cmake_parse_arguments(
    ARG
    ""
    "NAME;PROPERDOCS_CONFIG;API_SOURCE_DIRECTORY;API_PATH;OUTPUT_DIRECTORY;MULTIVERSION_DEFAULT_VERSION;DOXYGEN_OUTPUT_DIRECTORY;INSTALL_DIRECTORY"
    ""
    ${ARGN}
  )
  _besa_require_no_unparsed("besa_add_user_docs" "${ARG_UNPARSED_ARGUMENTS}")
  _besa_require_value("besa_add_user_docs" "NAME" "${ARG_NAME}")
  _besa_require_value("besa_add_user_docs" "PROPERDOCS_CONFIG" "${ARG_PROPERDOCS_CONFIG}")
  _besa_require_value(
    "besa_add_user_docs" "API_SOURCE_DIRECTORY" "${ARG_API_SOURCE_DIRECTORY}"
  )

  if(NOT ARG_API_PATH)
    set(ARG_API_PATH "reference/api")
  endif()
  string(REGEX REPLACE "^/+|/+$" "" ARG_API_PATH "${ARG_API_PATH}")
  if(ARG_API_PATH STREQUAL "")
    message(FATAL_ERROR "besa_add_user_docs: API_PATH must not resolve to the site root")
  endif()

  if(NOT ARG_OUTPUT_DIRECTORY)
    set(ARG_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/doc/site")
  endif()
  if(NOT ARG_MULTIVERSION_DEFAULT_VERSION)
    set(ARG_MULTIVERSION_DEFAULT_VERSION "main")
  endif()
  if(NOT ARG_DOXYGEN_OUTPUT_DIRECTORY)
    set(ARG_DOXYGEN_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/doc/doxygen")
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

  find_program(_besa_properdocs NAMES properdocs)
  if(NOT _besa_properdocs)
    message(
      FATAL_ERROR
      "besa_add_user_docs: properdocs was not found. Install ProperDocs before enabling the "
      "user-docs feature."
    )
  endif()

  set(_besa_properdocs_target "${ARG_NAME}.properdocs")
  set(_besa_api_target "${ARG_NAME}.api")
  set(_besa_api_multiversion_target "${ARG_NAME}.multiversion")
  set(_besa_properdocs_output "${PROJECT_BINARY_DIR}/doc/properdocs")
  set(_besa_api_output "${PROJECT_BINARY_DIR}/doc/api/current")
  set(_besa_api_multiversion_output "${PROJECT_BINARY_DIR}/doc/api/multiversion")

  # reference/api/<version>/ is three levels below the site root. Derive the number rather than
  # hard-code it so projects may mount the API reference elsewhere without changing conf.py.
  string(REPLACE "/" ";" _besa_api_path_parts "${ARG_API_PATH}")
  list(FILTER _besa_api_path_parts EXCLUDE REGEX "^$")
  list(LENGTH _besa_api_path_parts _besa_api_path_depth)
  math(EXPR _besa_site_root_depth "${_besa_api_path_depth} + 1")

  besa_add_sphinx_breathe_docs(
    NAME "${_besa_api_target}"
    SOURCE_DIRECTORY "${ARG_API_SOURCE_DIRECTORY}"
    OUTPUT_DIRECTORY "${_besa_api_output}"
    MULTIVERSION_NAME "${_besa_api_multiversion_target}"
    MULTIVERSION_OUTPUT_DIRECTORY "${_besa_api_multiversion_output}"
    MULTIVERSION_DEFAULT_VERSION "${ARG_MULTIVERSION_DEFAULT_VERSION}"
    DOXYGEN_OUTPUT_DIRECTORY "${ARG_DOXYGEN_OUTPUT_DIRECTORY}"
    SITE_ROOT_DEPTH "${_besa_site_root_depth}"
    NO_INSTALL
  )

  add_custom_target(
    "${_besa_properdocs_target}"
    COMMAND
      "${_besa_properdocs}" build
      --config-file "${_besa_properdocs_config}"
      --site-dir "${_besa_properdocs_output}"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMENT "Generating the ProperDocs documentation site"
    VERBATIM
  )

  add_custom_target(
    "${ARG_NAME}"
    COMMAND
      "${CMAKE_COMMAND}"
      "-DPROPERDOCS_DIRECTORY=${_besa_properdocs_output}"
      "-DAPI_DIRECTORY=${_besa_api_multiversion_output}"
      "-DOUTPUT_DIRECTORY=${ARG_OUTPUT_DIRECTORY}"
      "-DAPI_PATH=${ARG_API_PATH}"
      -P "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/userdocs/assemble-site.cmake"
    COMMENT "Assembling ProperDocs with the versioned API reference"
    VERBATIM
  )
  add_dependencies("${ARG_NAME}" "${_besa_properdocs_target}" "${_besa_api_multiversion_target}")

  # The final assembled tree is the only high-level installation artifact. Documentation remains an
  # optional build product: ordinary package installation succeeds when user.docs was not built.
  install(
    DIRECTORY "${ARG_OUTPUT_DIRECTORY}/"
    DESTINATION "${ARG_INSTALL_DIRECTORY}"
    OPTIONAL
  )
endfunction()
