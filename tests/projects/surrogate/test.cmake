# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Test-only mutation for the negative surrogate-header test.
function(_besa_test_surrogate)
  if(SURROGATE_BROKEN)
    besa_add_library(NAME liboops STATIC INSTALL NO)
    target_include_directories(liboops PUBLIC "${PROJECT_SOURCE_DIR}/oops")
    target_sources(liboops PRIVATE "${PROJECT_SOURCE_DIR}/oops.cpp")
  endif()
endfunction()
cmake_language(DEFER CALL _besa_test_surrogate)
