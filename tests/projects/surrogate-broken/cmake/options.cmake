# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Project configuration is declared here and consumed after finalization.
set(BUILD_DEVTOOLS "none" CACHE STRING "Enabled development tools")
set(BUILD_WARNINGS "minimal" CACHE STRING "Warning policies")
option(BUILD_TESTING "Build tests" ON)
besa_register_options(GROUP build VARIABLES BUILD_DEVTOOLS BUILD_WARNINGS BUILD_TESTING)
besa_finalize_options()
