# C++ project layout

The generated starter project contains a single C++ source root below `src/`:

```text
project/
├── cmake/
│   └── besa/
├── properdocs.yml
├── docs/                       # ProperDocs site source
│   ├── CMakeLists.txt
│   ├── index.md
│   └── reference/
│       └── index.md
├── api-docs/                   # Doxygen/Breathe/Sphinx API source
│   ├── conf.py
│   ├── Doxyfile
│   ├── index.rst
│   ├── api.rst
│   └── _templates/
│       └── versioning.html
├── src/
│   ├── CMakeLists.txt
│   └── cpp/
│       ├── bin/
│       ├── include/
│       │   └── <project>/
│       └── lib/
│           └── <project>/
├── test/
├── project/
└── showcase/
```

`src/CMakeLists.txt` contains the `besa_add_source_directory()` call for the C++ source root. The
generated project's main library lives below `src/cpp/lib/<project>/`. Additional language roots
can be added explicitly when a project needs them; they are not part of the starter source tree.

`project/` and `showcase/` use feature selectors so long-lived experiments and demonstrations remain
isolated from the production source graph.


## User-documentation layout

`docs/` is the ProperDocs source tree and therefore owns the canonical site hierarchy. `api-docs/`
is intentionally separate: Doxygen generates XML only, Breathe imports that XML into Sphinx, and
sphinx-multiversion rebuilds the API renderer for `main` plus the historical refs selected by BESA.
The default is every tag; projects can choose `latest:N`, a version range, or an exact ref set. BESA
mounts the resulting API trees below `reference/api/<version>/` when assembling `user.docs`.

This separation lets `properdocs serve` remain a normal local authoring workflow while API generation
can evolve independently. The build-tree Doxygen XML location is checkout-specific so simultaneous
or historical API builds do not share extraction state.

For each API build, `api-docs/conf.py` stages a synthetic header tree containing checked-in headers
from every `src/*/include/` root, developer-facing headers from `test/base/*/include/`, and public
headers from every configured `generated/<generator>/include/` root. The version metadata generator
is named `meta`, but the docs pipeline does not special-case it. Doxygen receives only the merged
tree and strips its staging roots, so repository layout details do not leak into the API file view.
The public part still mirrors the installed `include/` namespace, while test support appears beside it:

```text
Files
├── <project>/
│   ├── <project>.hpp
│   └── version.hpp
└── test<project>/
    └── ... developer test support ...
```

Repository-only components such as `src/`, `test/base/`, `cpp/`, `include/`, `lib/`, and `bin/`
therefore do not become levels in the API file hierarchy.
