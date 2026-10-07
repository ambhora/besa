# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.25)
project(
  besa
  VERSION 0.4.2
  DESCRIPTION "Declarative CMake project model and build runtime"
  LANGUAGES NONE
)

include(CMakePackageConfigHelpers)
include(CTest)

# --------------------------------------------------------------------------------------------------
# Package
# --------------------------------------------------------------------------------------------------
# The package is architecture independent: it is installed below share/ where find_package() looks
# for <prefix>/share/<name>*/cmake/ on every platform. GNUInstallDirs is deliberately not used: it
# needs an enabled language to choose a library directory, and BESA installs no libraries.
set(BESA_INSTALL_DATADIR "share" CACHE STRING
  "Installation directory of architecture-independent data, relative to the prefix"
)
set(BESA_INSTALL_CMAKEDIR "${BESA_INSTALL_DATADIR}/besa/cmake" CACHE STRING
  "Installation directory of the BESA CMake package, relative to the prefix"
)

# Requests for any version up to the installed one are accepted, matching the previous hand-written
# besaConfigVersion.cmake.
write_basic_package_version_file(
  "${PROJECT_BINARY_DIR}/besaConfigVersion.cmake"
  VERSION "${PROJECT_VERSION}"
  COMPATIBILITY AnyNewerVersion
  ARCH_INDEPENDENT
)

install(
  DIRECTORY "${PROJECT_SOURCE_DIR}/share/besa/cmake/"
  DESTINATION "${BESA_INSTALL_CMAKEDIR}"
)
install(
  FILES "${PROJECT_BINARY_DIR}/besaConfigVersion.cmake"
  DESTINATION "${BESA_INSTALL_CMAKEDIR}"
)
install(
  FILES "${PROJECT_SOURCE_DIR}/LICENSES/Apache-2.0.txt"
  DESTINATION "${BESA_INSTALL_DATADIR}/besa/licenses"
)

# --------------------------------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------------------------------
if(BUILD_TESTING)
  add_subdirectory(tests)
endif()
