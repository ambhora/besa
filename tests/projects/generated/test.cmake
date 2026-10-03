# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Test-only assertions for the generated-type example.
function(_besa_test_generated)
  if(NOT TARGET jnum.generate OR NOT TARGET libgenerated)
    message(FATAL_ERROR "generated type did not create expected targets")
  endif()
endfunction()
cmake_language(DEFER CALL _besa_test_generated)
