# Contributing

BESA is a small code base — about 4 000 lines of CMake under
`share/besa/cmake/` plus a tiny Python package — with a test suite that
configures, builds and tests real projects against an installed copy of the
modules. This page covers how it is organized and how to run the tests.

## Repository layout

```text
share/besa/cmake/      the CMake package (what find_package(besa) loads)
  besaConfig.cmake     entry point; includes every module once
  internal.cmake       argument checking, lifecycle guards, name normalization
  feature.cmake        features, finalization
  keyso.cmake          feature-space algebra
  subdirectory.cmake   unit types, directory lowering
  target.cmake         besa_add_library / besa_add_executable
  test.cmake           test discovery
  testmode.cmake       test modes
  devtools.cmake       devtool resolution; asan/lsan/ubsan/coverage/format/tidy/surrogate modules
  warning.cmake        warning policies
  version.cmake        release metadata, version.hpp
  manifest.cmake       manifest.json, besa_register_options
  package.cmake        install/export/CPS/installation manifest
  dependency.cmake     besa_dependency_add
  codegen.cmake        generated-unit bookkeeping
  cpdocs.cmake         cpdocs metadata exchange
  userdocs.cmake       documentation targets
  workspace.cmake      build/besa/ layout
  finalize.cmake       deferred finalizer ordering
src/besa/              the Python package (besa vendor)
tests/                 the CMake test suite and its fixture projects
dev/                   besa-dev: the CI compiler matrix tooling
```

Every module has a `Public API` section and an `Internal implementation`
section. Public commands use named arguments only; `_besa_`-prefixed
helpers are internal and may use positional arguments.

## Running the tests

The suite stages an installation of BESA into the build tree, then runs
each fixture project under `tests/projects/` through configure, build,
`ctest` and (where applicable) install and a downstream consumer build.
This means the tests exercise exactly what `find_package(besa)` delivers.

```bash
cmake -S . -B build -DBUILD_TESTING=ON
ctest --test-dir build --output-on-failure
```

Useful variations:

```bash
CC=clang CXX=clang++ ctest --test-dir build          # another toolchain, same build tree
ctest --test-dir build -L feature                    # one area: package core feature testmode version warning devtool options
ctest --test-dir build -R layout.cpp                 # one fixture
cmake -S . -B build -DBUILD_TESTING=ON -DBESA_TEST_CMAKE_ARGS="-DCMAKE_CXX_FLAGS=-O1"
```

The driver passes `-DCMAKE_CXX_STANDARD=20 -DCMAKE_BUILD_TYPE=Debug` to
every fixture; `BESA_TEST_CMAKE_ARGS` adds more, and `BESA_TEST_GENERATOR`
chooses the generator for fixtures. Tests that need `clang-format`,
`clang-tidy`, `gcovr` or `llvm-cov` are registered only when the tool is
found.

The Python package has its own tests:

```bash
uv run --group dev pytest        # or: hatch run test
uv run --group dev ruff check src/besa tests/python
```

### The compiler matrix

CI runs the suite in containers for every compiler in
`dev/etc/compilers.json`. The same containers can be run locally:

```bash
uv run --project dev besa-dev list            # configured compilers
uv run --project dev besa-dev run gcc-16      # run the suite in that container
uv run --project dev besa-dev discover        # check upstream for new major versions
```

Adding a compiler *version* needs no changes — discovery picks up new
majors above each family's `minimum`. Adding a *family* means a new entry
in `families`. See `dev/readme.md`.

## Writing a fixture project

Fixtures double as examples, so they are held to a standard:

- Each fixture owns a `cmake/options.cmake` that declares normal cache
  variables, registers them, and calls `besa_finalize_options()` once.
  `CMakeLists.txt` includes it right after `find_package(besa)`.
- The driver overrides project options (`BUILD_DEVTOOLS`, `TEST_MODE`,
  `PROJECT_FEATURE`, …) on the command line. Fixtures must not invent
  test-only selectors; a test directory that should exist only under
  AddressSanitizer uses `DEVTOOLS asan`, not `-DWITH_ASAN_TESTS=ON`.
- Keep the example copyable. Put harness-only assertions *after* the
  example under a `# TESTING` heading, or in a separate `test.cmake`
  (injected with `CMAKE_PROJECT_INCLUDE`) or `check-*.cmake` (run after
  configure via `CHECK`).
- For intentionally invalid usage, write a small negative fixture and
  register it with `EXPECT CONFIGURE_FAIL MATCH "<regex>"` rather than
  branching on an undocumented flag.
- In `ARGS`, the driver expands `@BINARY_DIR@` and `@SOURCE_DIR@`.

Register the fixture in `tests/CMakeLists.txt`:

```cmake
besa_project_test(NAME layout.my-case PROJECT my-case
  ARGS -DBUILD_DEVTOOLS=asan
  EXPECT PASS                      # or CONFIGURE_FAIL | BUILD_FAIL | TEST_FAIL
  CHECK my-case/check.cmake        # optional post-configure assertions
  CONSUMER my-case-consumer        # optional: install, then build this against it
  LABELS core
)
```

## Conventions

- CMake 4.3 is the minimum; use its features (file sets, `DEFER`,
  `install(PACKAGE_INFO)`) rather than working around their absence.
- BESA never sets language standards, compilers or build types.
- New capabilities (devtools, warning policies) are added to BESA's
  catalog, not declared per project.
- Every file carries the SPDX header; the repository is
  [REUSE](https://reuse.software/) compliant.
- Public functions validate their arguments and fail with
  `<command>: <message>`.

## Building this documentation

```bash
pip install properdocs properdocs-theme-readthedocs
properdocs serve          # live preview at http://127.0.0.1:8000/
properdocs build          # static site in site/
```

The configuration is `properdocs.yml` at the repository root; sources are
under `docs/`.
