# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Project configuration is declared here and consumed after finalization.
set(BUILD_DEVTOOLS "none" CACHE STRING "Enabled development tools")
option(BUILD_TESTING "Build tests" ON)
set(TEST_MODE "ci-commit" CACHE STRING "Selected test mode")
set_property(CACHE TEST_MODE PROPERTY STRINGS ci-commit ci-merge)
besa_test_modes_add(MODES ci-commit ci-merge)
besa_test_modes_default(MODES ci-commit)
besa_register_options(GROUP build VARIABLES BUILD_DEVTOOLS BUILD_TESTING TEST_MODE)
besa_finalize_options()
