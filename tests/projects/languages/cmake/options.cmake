# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Project configuration is declared here and consumed after finalization.
set(PROJECT_FEATURE "host" CACHE STRING "Selected features")
besa_set_feature_variable(PROJECT_FEATURE)
besa_add_feature(host)
besa_add_feature(gpu)
besa_keyso_one_of(backend host gpu)
besa_set_feature_space(backend DEFAULT host)
besa_register_options(GROUP project VARIABLES PROJECT_FEATURE)
besa_finalize_options()
