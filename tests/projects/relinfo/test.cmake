# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Test-only assertions and compile definitions for the release-info example.
function(_besa_test_relinfo)
  if(NOT PROJECT_SEMVER STREQUAL EXPECTED_SEMVER)
    message(FATAL_ERROR "PROJECT_SEMVER is '${PROJECT_SEMVER}', expected '${EXPECTED_SEMVER}'")
  endif()
  target_compile_definitions(relinfo.release.t PRIVATE "EXPECTED_RELEASE=\"${EXPECTED_RELEASE}\"")
endfunction()
cmake_language(DEFER CALL _besa_test_relinfo)
