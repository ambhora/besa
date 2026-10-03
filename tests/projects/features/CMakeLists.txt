# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Feature spaces are finite and enumerable. Feature names describe project capabilities; they are
# intentionally independent of source languages such as C++, CUDA, or HIP.
cmake_minimum_required(VERSION 3.25)
project(features VERSION 1.0.0 LANGUAGES NONE)
find_package(besa CONFIG REQUIRED)

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
besa_configure_complete()

besa_add_subdirectory(DIRECTORY alpha TYPE cpp CONDITION alpha)
besa_add_subdirectory(DIRECTORY beta TYPE cpp CONDITION beta)
