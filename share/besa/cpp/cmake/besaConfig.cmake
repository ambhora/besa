# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# BESA CMake package entry point.
#
# Generated projects vendor this directory and prepend it to CMAKE_PREFIX_PATH before calling
# find_package(besa CONFIG REQUIRED).  There is therefore no dependency on a globally installed BESA
# package after generation.  `besa cpp update` can replace this entire project-owned directory later.

include_guard(GLOBAL)
set(besa_VERSION "0.1.0")
set(CMAKE_FIND_PACKAGE_PREFER_CONFIG TRUE)

include("${CMAKE_CURRENT_LIST_DIR}/internal.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/selector.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/warning.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/format.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/tidy.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/surrogate.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/devtools.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/testmode.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/generated.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/version.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/package.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/target.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/dependency.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/directory.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/test.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/userdocs.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/finalize.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/feature.cmake")
