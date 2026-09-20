# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
besa_add_user_docs(
  NAME user.docs
  PROPERDOCS_CONFIG "${PROJECT_SOURCE_DIR}/properdocs.yml"
  CPDOC_CONFIG "${PROJECT_SOURCE_DIR}/cpdoc.yml"
  OUTPUT_DIRECTORY "${BESA_DOCS_DIRECTORY}/site"
)
