# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Install BESA from BINARY_DIR into a clean PREFIX for the project tests.
foreach(_required BINARY_DIR PREFIX CMAKEDIR)
  if(NOT DEFINED ${_required})
    message(FATAL_ERROR "stage.cmake: ${_required} is required")
  endif()
endforeach()
file(REMOVE_RECURSE "${PREFIX}")
execute_process(
  COMMAND "${CMAKE_COMMAND}" --install "${BINARY_DIR}" --prefix "${PREFIX}"
  COMMAND_ERROR_IS_FATAL ANY
)
foreach(_file besaConfig.cmake besaConfigVersion.cmake workspace.cmake)
  if(NOT EXISTS "${PREFIX}/${CMAKEDIR}/${_file}")
    message(FATAL_ERROR "stage.cmake: ${_file} was not installed")
  endif()
endforeach()
