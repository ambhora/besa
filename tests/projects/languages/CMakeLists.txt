# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# A feature selects project topology; TYPE independently states the language of the selected unit.
cmake_minimum_required(VERSION 3.25)
project(languages VERSION 1.0.0 LANGUAGES NONE)
find_package(besa CONFIG REQUIRED)

besa_add_feature(host)
besa_add_feature(gpu)
besa_keyso_one_of(backend host gpu)
besa_set_feature_space(backend DEFAULT host)
besa_configure_complete()

besa_add_subdirectory(DIRECTORY host TYPE cpp CONDITION host)
besa_add_subdirectory(DIRECTORY device TYPE cuda CONDITION gpu)
