# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
besa_compile_test_add_directory(
  NAME cpp
  PREFIX compile
  LABELS compile production
  TARGET_LIST vorlage::libvorlage
  MODES ci-commit
)
