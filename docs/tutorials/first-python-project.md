<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Create a Python project

Python generation is intentionally minimal for now. Create an empty directory whose name is the
project name and run BESA inside it:

```console
mkdir example_python
cd example_python
besa python generate
```

BESA copies the Python template into the current directory and substitutes the directory name for the
`vorlage` token. The generated project uses a `src/` package layout and `pyproject.toml`.

Run its tests with uv:

```console
uv run --group test pytest
```

The Python command currently has no update operation because it does not vendor a BESA runtime/build
module.
