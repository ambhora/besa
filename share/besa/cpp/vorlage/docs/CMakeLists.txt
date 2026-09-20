# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# ProperDocs builds two deliberately separate sites: the non-versioned project documentation and
# the versioned semantic API reference. The final user.docs target may assemble both trees for a
# single static deployment, but their versioning semantics remain independent.
besa_add_user_docs(
  NAME user.docs
  PROPERDOCS_CONFIG "${PROJECT_SOURCE_DIR}/properdocs.yml"
  API_SOURCE_DIRECTORY "${PROJECT_SOURCE_DIR}/api-docs"
  API_PATH reference/api
  OUTPUT_DIRECTORY "${BESA_DOCS_DIRECTORY}/site"
  MULTIVERSION_DEFAULT_VERSION main
)
