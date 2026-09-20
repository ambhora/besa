<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# BESA monorepo

This repository contains three independently testable Python projects:

- `besa/` — declarative project-development tooling and the CMake/Python project templates.
- `cpdoc/` — standalone semantic, versioned API documentation generation.
- `properdocs-cpdoc/` — the ProperDocs plugin that mounts cpdoc output and resolves API links.

The repository root is a uv workspace so the projects can use one lock file while retaining their own
`pyproject.toml`, source tree, and test suite.

Run the test suites independently with:

```console
uv run --project besa --group test pytest
uv run --project cpdoc --group test pytest
uv run --project properdocs-cpdoc --group test pytest
```

Build the BESA project website with:

```console
uv run --project besa --group docs properdocs build --config-file besa/properdocs.yml
```
