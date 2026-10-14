# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Test-only cpdocs selection. The example CMakeLists.txt remains ordinary BESA usage.
if(SELECT_GPU_FROM_CPDOCS)
  set(FEATURE_SET_PATH "${PROJECT_BINARY_DIR}/feature-set.json")
  file(WRITE "${FEATURE_SET_PATH}" "{\n  \"cpdocs-feature-set\": 1,\n  \"features\": [\"gpu\"]\n}\n")
  set(BESA_CPDOCS_FEATURE_SET "${FEATURE_SET_PATH}" CACHE FILEPATH "" FORCE)
  set(BESA_CPDOCS_MANIFEST_OUTPUT "${PROJECT_BINARY_DIR}/cpdocs-manifest.json" CACHE FILEPATH "" FORCE)
endif()
