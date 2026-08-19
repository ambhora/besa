# C++ project layout

The generated project uses language-specific roots below `src/`:

```text
project/
├── cmake/
│   └── besa/
├── properdocs.yml
├── docs/                       # ProperDocs site source
│   ├── CMakeLists.txt
│   ├── index.md
│   └── reference/
│       ├── index.md
│       └── api.md
├── api-docs/                   # Doxygen/Breathe/Sphinx API source
│   ├── conf.py
│   ├── Doxyfile
│   ├── index.rst
│   ├── api.rst
│   └── _templates/
│       └── versioning.html
├── src/
│   ├── CMakeLists.txt
│   ├── cpp/
│   │   ├── bin/
│   │   ├── include/
│   │   └── lib/
│   ├── c/
│   │   ├── bin/
│   │   ├── include/
│   │   └── lib/
│   └── cuda/
│       ├── bin/
│       ├── include/
│       └── lib/
├── test/
├── project/
└── showcase/
```

`src/CMakeLists.txt` contains `besa_add_source_directory()` calls. `project/` and `showcase/` use
feature selectors so long-lived experiments and demonstrations remain isolated from the production
source graph.

HIP and ASM source roots use the same `include/`, `lib/`, and `bin/` convention as the C-family
roots. A project can therefore use `src/hip` with `LANGUAGE HIP` and `src/asm` with `LANGUAGE ASM`
without changing the surrounding source-directory model.

For Fortran, BESA reserves the possibility of adding a `mod/` convention in a future release without
requiring existing project-level CMake descriptions to change.


## User-documentation layout

`docs/` is the ProperDocs source tree and therefore owns the canonical site hierarchy. `api-docs/`
is intentionally separate: Doxygen generates XML only, Breathe imports that XML into Sphinx, and
sphinx-multiversion rebuilds the API renderer from historical Git branch heads and tags. BESA mounts
the resulting API trees below `reference/api/<version>/` when assembling `user.docs`.

This separation lets `properdocs serve` remain a normal local authoring workflow while API generation
can evolve independently. The build-tree Doxygen XML location is checkout-specific so simultaneous
or historical API builds do not share extraction state.
