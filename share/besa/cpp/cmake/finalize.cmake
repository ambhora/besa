# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
include_guard(GLOBAL)

function(_besa_project_finalize)
  _besa_api_manifest_finalize()
  _besa_devtools_finalize()
  _besa_generated_prefixes_finalize()
  _besa_package_finalize()
endfunction()
