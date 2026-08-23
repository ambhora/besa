# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# The starter project contains one C++ source root using BESA's include/lib/<library>/bin convention.
# This file does not enable languages itself: toolchain features were already resolved by
# besa_configure_complete().

besa_add_source_directory(
  NAME cpp
  LANGUAGE CXX
  WHEN ALL_OF toolchain-cpp
)
