# BESA

BESA is a helper CMake package for writing CMake projects in a declarative
manner. A project states its libraries, the source trees that implement them,
the optional features it supports and where its tests are; BESA lowers that
description into ordinary CMake targets, CTest tests and install rules.

Because the project is described rather than scripted, BESA can also read
the description back. It inserts hooks into the CMake configure step that
emit machine-readable build descriptions — which source units exist, in
which language, under which features, with which options — for other tools
to consume. The [cpdocs](https://github.com/ambhora/cpdocs) API
documentation generator is one such consumer; CI matrix generators and
packaging tools are others.

## A complete project

```cmake
# Target CMake 4.3: BESA uses file sets, deferred calls and install(PACKAGE_INFO).
cmake_minimum_required(VERSION 4.3)

# No language is enabled here; BESA enables each language when a source unit
# of that language is attached.
project(greet VERSION 1.2.0 LANGUAGES NONE)

# Load BESA. From this point until besa_finalize_options() the configuration
# is open: features, test modes and options may be declared.
find_package(besa CONFIG REQUIRED)

# An ordinary cache variable carries the user's feature selection
# (-DPROJECT_FEATURE="gpu").  BESA validates it against the declared features.
set(PROJECT_FEATURE "none" CACHE STRING "Selected project features")
besa_set_feature_variable(PROJECT_FEATURE)

# Declare one optional capability of the project.
besa_add_feature(gpu)

# Ordinary cache variables for BESA-owned selections: instrumentation
# (asan, ubsan, coverage, ...) and warning policy.
set(BUILD_DEVTOOLS "none" CACHE STRING "Enabled development tools")
set(BUILD_WARNINGS "minimal" CACHE STRING "Warning policies")
option(BUILD_TESTING "Build tests" ON)

# Record the variables in the manifest so tools can present them.
besa_register_options(GROUP project VARIABLES PROJECT_FEATURE)
besa_register_options(GROUP build VARIABLES BUILD_DEVTOOLS BUILD_WARNINGS BUILD_TESTING)

# Resolve and validate everything declared above, then freeze the
# configuration.  Targets may be created from here on.
besa_finalize_options()
include(CTest)

# Create the library target.  The alias greet::libgreet is created, the
# output file is libgreet.a (not liblibgreet.a), and the target is
# registered for installation and export.
besa_add_library(NAME libgreet)

# Attach a C++ source unit: src/include/** becomes a public header file set,
# src/lib/** becomes private sources compiled as C++.  This call enables CXX.
besa_add_directory(LIBRARY libgreet ROOT src TYPE cpp)

# Attach a second unit only when the gpu feature is enabled.  The feature
# (gpu) and the language of the unit (cuda) are independent.
besa_add_directory(LIBRARY libgreet ROOT gpu TYPE cuda CONDITION gpu)

# Create one executable per file in bin/: bin/greet-cli.cpp -> greet-cli.
# Nothing is linked implicitly.
besa_add_subdirectory(DIRECTORY bin TYPE bin)
target_link_libraries(greet-cli PRIVATE greet::libgreet)

# Discover tests from tests/**/*.t.cpp.  tests/parse.t.cpp becomes the
# CTest test greet.parse.t; a .fail.t.cpp file is expected to fail.
if(BUILD_TESTING)
  besa_test_add_directory(NAME tests PREFIX greet TARGET_LIST greet::libgreet)
endif()
```

Configuring this project produces the usual build system plus the
following outputs, none of which the project wrote by hand:

- `greet/version.hpp`, a generated header exposing the version, release
  channel and build information as `constexpr` values, attached to every
  library.
- `make install` with `greetConfig.cmake`, an exported `greet::libgreet`
  target, a CPS package description and an installation manifest, so a
  downstream `find_package(greet)` works without BESA.
- Sanitizer, coverage, clang-format and clang-tidy runs selected with
  `-DBUILD_DEVTOOLS=...`.
- `build/besa/manifest.json`, the build description (abbreviated here; every unit record carries the full field set):

```json
{
  "besa-manifest": 1,
  "project": "greet",
  "features": ["gpu"],
  "feature_configuration": {
    "variable": "PROJECT_FEATURE",
    "available": ["gpu"],
    "explicit_space": "",
    "conflicts": []
  },
  "options": [
    {"name": "PROJECT_FEATURE", "group": "project", "type": "STRING", "value": "gpu",
     "description": "Selected project features", "allowed": []},
    {"name": "BUILD_DEVTOOLS", "group": "build", "type": "STRING", "value": "none",
     "description": "Enabled development tools", "allowed": []}
  ],
  "units": [
    {"id": "src", "type": "cpp",  "language": "cpp",  "generated": false,
     "headers": ["/work/greet/src/include"], "sources": ["/work/greet/src/lib"],
     "parse": {"language": "cpp", "standard": "c++20",
               "compile-database": "/work/greet/build/compile_commands.json"}},
    {"id": "gpu", "type": "cuda", "language": "cuda", "generated": false,
     "headers": ["/work/greet/gpu/include"], "sources": ["/work/greet/gpu/lib"],
     "parse": {"language": "cpp", "compile-database": "/work/greet/build/compile_commands.json"}},
    {"id": "bin", "type": "bin",  "language": null,
     "executables": ["/work/greet/bin/greet-cli.cpp"]}
  ]
}
```

On request, BESA also enumerates every valid feature combination
(`feature-sets.json`) so that a tool can configure and document each one.
The [manifest reference](reference/manifest.md) describes the formats.

## Why BESA

CMake projects of any size tend to re-implement the same machinery:
globbing source trees, declaring header sets, writing install and export
rules, attaching sanitizer flags behind an `option()`, and inventing a
scheme for build variants. BESA replaces that machinery with a small
vocabulary. Each concept is declared once, in the project; BESA derives the
CMake from it and records it in the manifest.

| Concept | What the project writes | What BESA derives |
| --- | --- | --- |
| Source unit | A directory with `include/`, `lib/`, optionally `module/` or `mod/`, attached to a library with a language | Header file sets, include paths, private sources compiled in the declared language, language activation |
| Feature | `besa_add_feature(gpu)`; optionally which combinations are valid | Validation of the user's selection at configure time; `CONDITION gpu` on units, tests and dependencies |
| Test directory | `besa_test_add_directory(NAME tests)` with files named `*.t.cpp` | One executable and CTest test per file; `.fail.` and `.disabled.` expectations; test modes |
| Devtool selection | `-DBUILD_DEVTOOLS=asan;coverage` | Instrumentation on every target; format, lint, coverage and header checks as CTest tests |
| Installable target | `besa_add_library(NAME libgreet)` | Install rules, `greetConfig.cmake`, exported targets, CPS, installation manifest, `find_dependency()` calls |
| Manifest | nothing | `build/besa/manifest.json` describing units, languages, options and features |

The guide covers each row:
[Libraries and source units](guide/source-units.md),
[Features](guide/features.md),
[Tests](guide/testing.md),
[Developer tools](guide/devtools.md),
[Installation and packaging](guide/packaging.md),
[The manifest](reference/manifest.md).

## What BESA does *not* do

BESA is deliberately narrow about a few things:

- **It does not pick a language standard, compiler, or build type.** Select
  those with presets, toolchain files or `-D` options. BESA will not add
  `target_compile_features()` behind your back.
- **It does not infer link dependencies.** `target_link_libraries()` remains
  explicit, including for executables created from `bin/`.
- **It does not create a magic `lib<project>` target.** Every library is
  declared with `besa_add_library()`; all libraries are peers.
- **It does not hide CMake.** Every BESA target is an ordinary CMake target.
  You can call any `target_*()` command on it.

## Requirements

- CMake **4.3** or newer (BESA uses `cmake_language(DEFER)`, header and
  C++-module file sets, `install(PACKAGE_INFO)` and the reserved `codegen`
  target).
- Any CMake generator. Compiled tests in the BESA repository are run with GCC
  13–16 and Clang 21+; the BESA modules themselves are compiler-agnostic and
  apply compiler-specific flags only through generator expressions.
- Python 3.11+ only if you install BESA from PyPI or use `besa vendor`.

## Where to go next

- [Installation](getting-started/installation.md) — three ways to get the
  CMake package into your project.
- [Your first project](getting-started/first-project.md) — a complete
  walk-through from an empty directory to an installed package.
- [How a BESA project is configured](guide/lifecycle.md) — the one concept
  that explains every ordering rule: options are declared, frozen, and only
  then consumed.
- [Command reference](reference/commands.md) — every public command with its
  full signature.

BESA is licensed under the Apache License 2.0. Source code lives at
[github.com/ambhora/besa](https://github.com/ambhora/besa).
