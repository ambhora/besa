# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Project configuration is declared here and consumed after finalization.
set(PROJECT_FEATURE "alpha" CACHE STRING "Selected features")
besa_set_feature_variable(PROJECT_FEATURE)
besa_add_feature(alpha)
besa_add_feature(beta)
besa_add_feature(mpi)
besa_add_feature(gpu)
besa_keyso_one_of(implementation alpha beta)
besa_keyso_zero_or_one(parallel mpi)
besa_keyso_zero_or_one(acceleration gpu)
besa_keyso_create_feature_space(
  supported
  PRODUCT
  implementation
  parallel
  acceleration
)
besa_set_feature_space(supported DEFAULT alpha)
besa_register_options(GROUP project VARIABLES PROJECT_FEATURE)
besa_finalize_options()
