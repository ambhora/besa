<!--
--------------------------------------------------------------------------------------------------
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 besa developers
--------------------------------------------------------------------------------------------------
-->
# BESA

**A declarative project model for CMake.** Describe your libraries, their
source trees, the features they support and how they are tested; BESA turns
that into CMake targets, CTest tests, an installable package and a manifest
that documentation tools can read.

```cmake
cmake_minimum_required(VERSION 4.3)
project(greet VERSION 1.2.0 LANGUAGES NONE)
find_package(besa CONFIG REQUIRED)
include(cmake/options.cmake)                    # declares options, calls besa_finalize_options()
include(CTest)

besa_add_library(NAME libgreet)                          # greet::libgreet
besa_add_directory(LIBRARY libgreet ROOT src TYPE cpp)   # src/include/**, src/lib/**
besa_add_subdirectory(DIRECTORY bin TYPE bin)            # one executable per file in bin/
target_link_libraries(greet-cli PRIVATE greet::libgreet)

if(BUILD_TESTING)
  besa_test_add_directory(NAME tests PREFIX greet TARGET_LIST greet::libgreet)  # tests/**/*.t.cpp
endif()
```

That is a complete project with public headers, an installed CLI, a
discovered test suite, a generated `greet/version.hpp`, `make install` with
`greetConfig.cmake` and a CPS description, and sanitizers, coverage,
clang-format and clang-tidy one `-D` flag away.

## Highlights

- **Semantic source units** — `include/`, `lib/`, `module/`, `mod/` under a
  root, compiled in a declared language (`c`, `cpp`, `cuda`, `hip`,
  `fortran`), attached to any library. Several units per library, several
  libraries per project.
- **Features with validated combinations** — declare `gpu`, `mpi`, …; express
  "exactly one backend, optionally MPI" as a finite feature space; invalid
  selections fail at configure time with the rule that rejected them.
- **Tests by convention** — `name.t.cpp` is a test, `name.fail.t.cpp` must
  fail, `name.disabled.t.cpp` is disabled; compile-only tests; project-defined
  test modes (`ci-commit`, `ci-merge`).
- **One devtool switch** — `-DBUILD_DEVTOOLS="asan;ubsan;coverage;format;linting;surrogate"`
  instruments every target and registers the corresponding checks.
- **Packaging that works downstream** — `<Project>Config.cmake`, exported
  targets, CPS, an installation manifest and `find_dependency()` calls derived
  from `besa_dependency_add()`. Consumers never need BESA.
- **A manifest for tooling** — `build/besa/manifest.json` describes units,
  languages, options and features; [cpdocs](https://github.com/ambhora/cpdocs)
  builds versioned API documentation from it without a second project
  description.

## Install

```bash
# as a CMake package
cmake -S besa -B besa/build && cmake --install besa/build --prefix ~/.local

# or vendored into your repository
pip install besa && besa vendor      # writes cmake/besa/; then set(besa_DIR cmake/besa)
```

Requires CMake 4.3+. Tested with GCC 13–16 and Clang 21+.

## Documentation

Full documentation lives in [`docs/`](docs/index.md) and is built with
[ProperDocs](https://properdocs.org/) (`properdocs serve`):

- [Installation](docs/getting-started/installation.md) ·
  [Your first project](docs/getting-started/first-project.md) ·
  [Layout at a glance](docs/getting-started/layout.md)
- [How a BESA project is configured](docs/guide/lifecycle.md) ·
  [Libraries and source units](docs/guide/source-units.md) ·
  [Features](docs/guide/features.md) ·
  [Feature spaces](docs/guide/feature-spaces.md) ·
  [Tests](docs/guide/testing.md) ·
  [Developer tools](docs/guide/devtools.md) ·
  [Packaging](docs/guide/packaging.md)
- [Command reference](docs/reference/commands.md) ·
  [Cache variables](docs/reference/variables.md) ·
  [The manifest](docs/reference/manifest.md)

## Developing BESA

```bash
cmake -S . -B build -DBUILD_TESTING=ON && ctest --test-dir build --output-on-failure
uv run --project dev besa-dev run gcc-16     # the CI container for one compiler
```

See [Contributing](docs/contributing.md). Licensed under Apache-2.0.
