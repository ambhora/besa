# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Project configuration is declared here and consumed after finalization.
set(BUILD_DEVTOOLS "none" CACHE STRING "Enabled development tools")
set(BUILD_WARNINGS "minimal" CACHE STRING "Warning policies")
option(BUILD_TESTING "Build tests" ON)
besa_register_options(GROUP build VARIABLES BUILD_DEVTOOLS BUILD_WARNINGS BUILD_TESTING)
set(PKGBUILDER_ID "vanilla" CACHE STRING "ID of the package maintainer")
set(PKGBUILDER_REVISION "1" CACHE STRING "Package build revision")
set(RELEASE_TYPE "dev" CACHE STRING "Release type")
set_property(CACHE RELEASE_TYPE PROPERTY STRINGS dev release alpha beta rc)
set(RELEASE_REVISION "1" CACHE STRING "Release revision")
besa_register_options(GROUP packaging VARIABLES PKGBUILDER_ID PKGBUILDER_REVISION)
besa_register_options(GROUP release VARIABLES RELEASE_TYPE RELEASE_REVISION)
besa_finalize_options()
