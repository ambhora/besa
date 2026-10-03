# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Test-only assertions for the downstream-consumer example.
function(_besa_test_basic_consumer)
  # The default RELEASE_TYPE is dev, which yields dev.<branch>.<hash>.
  if(NOT basic_VERSION_STRING MATCHES "^dev\.")
    message(FATAL_ERROR "unexpected basic_VERSION_STRING '${basic_VERSION_STRING}'")
  endif()
endfunction()
cmake_language(DEFER CALL _besa_test_basic_consumer)
