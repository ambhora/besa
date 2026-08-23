# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
include_guard(GLOBAL)
include("${CMAKE_CURRENT_LIST_DIR}/internal.cmake")

function(_besa_git_value OUTPUT_VARIABLE)
  cmake_parse_arguments(ARG "" "COMMAND;FALLBACK" "" ${ARGN})
  find_program(_git git)
  if(NOT _git)
    set("${OUTPUT_VARIABLE}" "${ARG_FALLBACK}" PARENT_SCOPE)
    return()
  endif()
  separate_arguments(_command UNIX_COMMAND "${ARG_COMMAND}")
  execute_process(
    COMMAND "${_git}" ${_command}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    RESULT_VARIABLE _result
    OUTPUT_VARIABLE _value
    ERROR_QUIET
    OUTPUT_STRIP_TRAILING_WHITESPACE
  )
  if(NOT _result EQUAL 0 OR "${_value}" STREQUAL "")
    set(_value "${ARG_FALLBACK}")
  endif()
  string(REGEX REPLACE "[^A-Za-z0-9.-]" "." _value "${_value}")
  set("${OUTPUT_VARIABLE}" "${_value}" PARENT_SCOPE)
endfunction()

function(_besa_cpp_string_literal_escape OUTPUT_VARIABLE INPUT_VALUE)
  set(_value "${INPUT_VALUE}")
  string(REPLACE "\\" "\\\\" _value "${_value}")
  string(REPLACE "\"" "\\\"" _value "${_value}")
  set("${OUTPUT_VARIABLE}" "${_value}" PARENT_SCOPE)
endfunction()

function(_besa_version_resolve)
  if(NOT DEFINED RELEASE_TYPE)
    set(RELEASE_TYPE dev CACHE STRING "Type of release")
  endif()
  if(NOT DEFINED RELEASE_REVISION)
    set(RELEASE_REVISION 1 CACHE STRING "Revision of prerelease")
  endif()
  if(NOT DEFINED PKGBUILDER_ID)
    set(PKGBUILDER_ID "vanilla" CACHE STRING "Package builder identifier")
  endif()
  if(NOT DEFINED PKGBUILDER_REVISION)
    set(PKGBUILDER_REVISION "1" CACHE STRING "Package builder revision")
  endif()
  if(NOT RELEASE_TYPE MATCHES "^(dev|release|alpha|beta|rc)$")
    _besa_fatal(
      "besa_configure_complete"
      "invalid RELEASE_TYPE '${RELEASE_TYPE}'. Expected dev, release, alpha, beta, or rc"
    )
  endif()

  if(RELEASE_TYPE STREQUAL "release")
    set(_semver "${PROJECT_VERSION}")
    set(_release_enum "release")
    set(_release_string "release")
  elseif(RELEASE_TYPE STREQUAL "dev")
    _besa_git_value(_branch COMMAND "rev-parse --abbrev-ref HEAD" FALLBACK "nogit")
    _besa_git_value(_hash COMMAND "rev-parse --short HEAD" FALLBACK "nogit")
    set(_semver "dev.${_branch}.${_hash}")
    set(_release_enum "development")
    set(_release_string "dev")
  elseif(RELEASE_TYPE STREQUAL "alpha")
    set(_semver "${PROJECT_VERSION}-alpha.${RELEASE_REVISION}")
    set(_release_enum "alpha")
    set(_release_string "alpha.${RELEASE_REVISION}")
  elseif(RELEASE_TYPE STREQUAL "beta")
    set(_semver "${PROJECT_VERSION}-beta.${RELEASE_REVISION}")
    set(_release_enum "beta")
    set(_release_string "beta.${RELEASE_REVISION}")
  else()
    set(_semver "${PROJECT_VERSION}-rc.${RELEASE_REVISION}")
    set(_release_enum "release_candidate")
    set(_release_string "rc.${RELEASE_REVISION}")
  endif()

  set(PROJECT_SEMVER "${_semver}" CACHE INTERNAL "Resolved project semantic version")
  set(PROJECT_SEMVER "${_semver}" PARENT_SCOPE)

  string(REGEX REPLACE "[^A-Za-z0-9_]" "_" _namespace "${PROJECT_NAME}")
  besa_generated_include_add(NAME meta OUTPUT_VARIABLE _include_dir)
  set(_header_dir "${_include_dir}/${PROJECT_NAME}")
  file(MAKE_DIRECTORY "${_header_dir}")
  foreach(_component MAJOR MINOR PATCH TWEAK)
    if("${PROJECT_VERSION_${_component}}" STREQUAL "")
      set(_version_${_component} 0)
    else()
      set(_version_${_component} "${PROJECT_VERSION_${_component}}")
    endif()
  endforeach()

  if("${CMAKE_CXX_COMPILER_ID}" STREQUAL "")
    set(_build_compiler "unknown")
  else()
    set(_build_compiler "${CMAKE_CXX_COMPILER_ID}")
  endif()
  if("${CMAKE_CXX_COMPILER_VERSION}" STREQUAL "")
    set(_build_compiler_version "unknown")
  else()
    set(_build_compiler_version "${CMAKE_CXX_COMPILER_VERSION}")
  endif()
  if("${CMAKE_SYSTEM_NAME}" STREQUAL "")
    set(_build_system "unknown")
  else()
    set(_build_system "${CMAKE_SYSTEM_NAME}")
  endif()
  if("${CMAKE_SYSTEM_PROCESSOR}" STREQUAL "")
    set(_build_processor "unknown")
  else()
    set(_build_processor "${CMAKE_SYSTEM_PROCESSOR}")
  endif()
  if(NOT "${CMAKE_BUILD_TYPE}" STREQUAL "")
    set(_build_type "${CMAKE_BUILD_TYPE}")
  elseif(DEFINED CMAKE_CONFIGURATION_TYPES)
    set(_build_type "multi-config")
  else()
    set(_build_type "none")
  endif()
  set(_build_string
    "${_build_compiler} ${_build_compiler_version}; ${_build_system}/${_build_processor}; ${_build_type}"
  )

  foreach(_value IN ITEMS
      PROJECT_VERSION
      _release_string
      PKGBUILDER_ID
      PKGBUILDER_REVISION
      _build_compiler
      _build_compiler_version
      _build_system
      _build_processor
      _build_type
      _build_string
  )
    _besa_cpp_string_literal_escape(_escaped_${_value} "${${_value}}")
  endforeach()

  string(TOUPPER "${_namespace}" _header_guard_namespace)
  set(_header_guard "${_header_guard_namespace}_VERSION_HPP")

  set(_header_template [=[
// Generated by BESA.
#ifndef @HEADER_GUARD@
#define @HEADER_GUARD@

#include <cstdint>
#include <string_view>

namespace @PROJECT_NAMESPACE@::meta {

enum class release_type {
  development,
  release,
  alpha,
  beta,
  release_candidate,
};

struct semantic_version {
  std::uint32_t major;
  std::uint32_t minor;
  std::uint32_t patch;
  std::uint32_t tweak;
};

struct release_info {
  release_type type;
  std::uint32_t revision;
};

struct package_info {
  std::string_view builder;
  std::string_view revision;
};

struct build_info {
  std::string_view compiler;
  std::string_view compiler_version;
  std::string_view system;
  std::string_view processor;
  std::string_view build_type;
};

[[nodiscard]] inline constexpr semantic_version version() noexcept
{
  return {@VERSION_MAJOR@, @VERSION_MINOR@, @VERSION_PATCH@, @VERSION_TWEAK@};
}

[[nodiscard]] inline constexpr release_info release() noexcept
{
  return {release_type::@RELEASE_ENUM@, @RELEASE_REVISION_VALUE@};
}

[[nodiscard]] inline constexpr package_info package() noexcept
{
  return {"@PKGBUILDER_ID_VALUE@", "@PKGBUILDER_REVISION_VALUE@"};
}

[[nodiscard]] inline constexpr build_info build() noexcept
{
  return {
    "@BUILD_COMPILER@",
    "@BUILD_COMPILER_VERSION@",
    "@BUILD_SYSTEM@",
    "@BUILD_PROCESSOR@",
    "@BUILD_TYPE@",
  };
}

[[nodiscard]] inline constexpr std::string_view to_string(semantic_version) noexcept
{
  return "@PROJECT_VERSION_STRING@";
}

[[nodiscard]] inline constexpr std::string_view to_string(release_type value) noexcept
{
  switch (value) {
  case release_type::development:
    return "dev";
  case release_type::release:
    return "release";
  case release_type::alpha:
    return "alpha";
  case release_type::beta:
    return "beta";
  case release_type::release_candidate:
    return "rc";
  }
  return "unknown";
}

[[nodiscard]] inline constexpr std::string_view to_string(release_info) noexcept
{
  return "@RELEASE_STRING@";
}

[[nodiscard]] inline constexpr std::string_view to_string(build_info) noexcept
{
  return "@BUILD_STRING@";
}

} // namespace @PROJECT_NAMESPACE@::meta

#endif // @HEADER_GUARD@
]=])
  set(PROJECT_NAMESPACE "${_namespace}")
  set(HEADER_GUARD "${_header_guard}")
  set(VERSION_MAJOR "${_version_MAJOR}")
  set(VERSION_MINOR "${_version_MINOR}")
  set(VERSION_PATCH "${_version_PATCH}")
  set(VERSION_TWEAK "${_version_TWEAK}")
  set(RELEASE_ENUM "${_release_enum}")
  set(RELEASE_REVISION_VALUE "${RELEASE_REVISION}")
  set(PKGBUILDER_ID_VALUE "${_escaped_PKGBUILDER_ID}")
  set(PKGBUILDER_REVISION_VALUE "${_escaped_PKGBUILDER_REVISION}")
  set(PROJECT_VERSION_STRING "${_escaped_PROJECT_VERSION}")
  set(RELEASE_STRING "${_escaped__release_string}")
  set(BUILD_COMPILER "${_escaped__build_compiler}")
  set(BUILD_COMPILER_VERSION "${_escaped__build_compiler_version}")
  set(BUILD_SYSTEM "${_escaped__build_system}")
  set(BUILD_PROCESSOR "${_escaped__build_processor}")
  set(BUILD_TYPE "${_escaped__build_type}")
  set(BUILD_STRING "${_escaped__build_string}")
  string(CONFIGURE "${_header_template}" _header_text @ONLY)

  file(WRITE "${_header_dir}/version.hpp" "${_header_text}")
endfunction()
