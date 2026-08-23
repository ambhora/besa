# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# ProperDocs owns the documentation-site root. Doxygen/Breathe/Exhale/Sphinx provide only the versioned API
# reference mounted below reference/api/. The final user.docs target assembles both trees into one
# static artifact under <build>/doc/site.
besa_add_user_docs(
  NAME user.docs
  PROPERDOCS_CONFIG "${PROJECT_SOURCE_DIR}/properdocs.yml"
  API_SOURCE_DIRECTORY "${PROJECT_SOURCE_DIR}/api-docs"
  API_PATH reference/api
  OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/doc/site"
  MULTIVERSION_DEFAULT_VERSION main
  DOXYGEN_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/doc/doxygen"
)
