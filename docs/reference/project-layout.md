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
sphinx-multiversion rebuilds the API renderer from historical Git branch heads and tags. BESA mounts
the resulting API trees below `reference/api/<version>/` when assembling `user.docs`.

This separation lets `properdocs serve` remain a normal local authoring workflow while API generation
can evolve independently. The build-tree Doxygen XML location is checkout-specific so simultaneous
or historical API builds do not share extraction state.

For each API build, `api-docs/conf.py` stages a synthetic public-header tree containing checked-in
headers from every `src/*/include/` root plus public headers from every configured
`generated/<generator>/include/` root. The version metadata generator is named `meta`, but the docs
pipeline does not special-case it. Doxygen receives only the merged tree and strips its staging root,
so Exhale's file hierarchy mirrors the contents of an installed `include/` directory:

```text
Files
└── <project>/
    ├── <project>.hpp
    └── version.hpp
```

Repository-only components such as `src/`, `cpp/`, `include/`, `lib/`, and `bin/` therefore do not
become levels in the public API file hierarchy.
