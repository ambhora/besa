# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Each language-specific source root follows BESA's include/lib/bin convention.  This file does not
# enable languages itself: toolchain features were already resolved by besa_configure_complete().

besa_add_source_directory(
  NAME cpp
  LANGUAGE CXX
  WHEN ALL_OF toolchain-cpp
)

besa_add_source_directory(
  NAME c
  LANGUAGE C
  WHEN ALL_OF toolchain-c
)

besa_add_source_directory(
  NAME cuda
  LANGUAGE CUDA
  WHEN ALL_OF toolchain-cuda
)

besa_add_source_directory(
  NAME hip
  LANGUAGE HIP
  WHEN ALL_OF toolchain-hip
)

besa_add_source_directory(
  NAME asm
  LANGUAGE ASM
  WHEN ALL_OF toolchain-asm
)
