# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Project configuration is declared here and consumed after finalization.
set(PROJECT_FEATURE "none" CACHE STRING "Features")
set(BUILD_WARNINGS "minimal" CACHE STRING "Warnings")
option(BUILD_TESTING "Testing" OFF)
besa_set_feature_variable(PROJECT_FEATURE)
besa_add_feature(mpi)
besa_add_feature(gpu)
besa_features_conflict(mpi gpu)
besa_register_options(GROUP project VARIABLES PROJECT_FEATURE)
besa_register_options(GROUP build VARIABLES BUILD_WARNINGS BUILD_TESTING)
besa_finalize_options()
