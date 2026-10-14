# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
set(BUILD_DEVTOOLS "none" CACHE STRING "Enabled development tools")
set(BUILD_WARNINGS "minimal" CACHE STRING "Warning policy")
option(BUILD_TESTING "Build Tests" OFF)
set(TEST_MODE "commit" CACHE STRING "Test mode")
besa_test_modes_add(MODES commit)
besa_finalize_options()
