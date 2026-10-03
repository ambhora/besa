# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Test-only cpdocs selection. The example CMakeLists.txt remains ordinary BESA usage.
if(SELECT_GPU_FROM_CPDOCS)
  set(_feature_set "${PROJECT_BINARY_DIR}/feature-set.json")
  file(WRITE "${_feature_set}" "{\n  \"cpdocs-feature-set\": 1,\n  \"features\": [\"gpu\"]\n}\n")
  set(BESA_CPDOCS_FEATURE_SET "${_feature_set}" CACHE FILEPATH "" FORCE)
  set(BESA_CPDOCS_MANIFEST_OUTPUT "${PROJECT_BINARY_DIR}/cpdocs-manifest.json" CACHE FILEPATH "" FORCE)
endif()
