<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# C++ project layout

The generated starter project has `besa.toml` as its authoritative project declaration and one C++
source prefix below `src/`:

```text
project/
├── besa.toml
├── CMakeLists.txt               # CMake backend bootstrap
├── cmake/
│   └── besa/
├── properdocs.yml
├── docs/                        # ProperDocs source
│   ├── CMakeLists.txt
│   ├── index.md
│   └── reference/
│       └── index.md
├── api-docs/                    # Doxygen/Breathe/Sphinx API source
│   ├── conf.py
│   ├── Doxyfile.in
│   ├── index.rst
│   ├── _static/
│   └── _templates/
├── src/
│   └── cpp/
│       ├── bin/
│       ├── include/
│       │   └── <project>/
│       └── lib/
│           └── <project>/
├── test/
├── project/
└── showcases/
```

The C++ source prefix is registered directly in `besa.toml`; there is no intermediate
`src/CMakeLists.txt` whose purpose is only to repeat that declaration. BESA owns prefix discovery and
creates the project library/executables from the conventional `include/`, `lib/`, `bin/`, and
optional `mod/` contents.

Likewise, `project/` and `showcases/` entries are ordinary conditional directory registrations in the
model. Their `project-*` and `showcase-*` names are feature metadata/conventions, not separate build
systems.

## Workspace layout

Generated state belongs to a workspace rather than to the project declaration:

```text
<workspace>/
├── build/                       # backend build state/artifacts
├── codegen/                     # generated prefixes
│   └── meta/
│       └── include/<project>/version.hpp
├── docs/                        # generated documentation
└── configure_cache/             # normalized model and analysis caches
```

The CMake backend uses the parent of `PROJECT_BINARY_DIR` as the default workspace; callers may set
`BESA_WORKSPACE` explicitly.

## User-documentation layout

`docs/` is the ProperDocs **source** tree and owns the canonical information architecture.
`api-docs/` is separate: Doxygen generates XML, Breathe imports it, Exhale creates entity pages, and
sphinx-multiversion rebuilds the API renderer for selected Git refs. Generated documentation is
written below `<workspace>/docs/`, and the assembled site mounts API versions below
`reference/api/<version>/`.

API discovery uses the profiles declared in `besa.toml`, merges their Doxygen models, annotates every
entity with profile availability, and generates an **API configuration** page describing the feature
and profile mappings used for the reference. Program listings are restored from the real source
files so whitespace, comments, preprocessor branches, portability macros, and physical line numbers
remain faithful to the checkout being documented.
