# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Test-only assertions for package discovery.
function(_besa_test_findpackage)
  if(NOT besa_VERSION VERSION_GREATER_EQUAL REQUESTED_VERSION)
    message(FATAL_ERROR "besa_VERSION '${besa_VERSION}' does not satisfy '${REQUESTED_VERSION}'")
  endif()
  set(_commands
    besa_configure_complete
    besa_add_feature
    besa_keyso_one_of
    besa_keyso_zero_or_one
    besa_keyso_create_feature_space
    besa_set_feature_space
    besa_add_subdirectory
    besa_workspace_initialize
  )
  foreach(_command IN LISTS _commands)
    if(NOT COMMAND "${_command}")
      message(FATAL_ERROR "besa does not provide ${_command}")
    endif()
  endforeach()
endfunction()
cmake_language(DEFER CALL _besa_test_findpackage)
