<!--
--------------------------------------------------------------------------------------------------
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 besa developers
--------------------------------------------------------------------------------------------------
-->
# BESA

BESA is a declarative CMake project model. Projects describe **features**, **valid feature spaces**, and
**semantic source units**; BESA lowers that model into CMake targets and a machine-readable manifest.
The same model is consumed by cpdocs, so documentation does not require a second project description.

Features and source languages are independent concepts. A project feature such as `gpu` may select a
CUDA source unit, but the feature is still just a project capability while `cuda` is the unit's language.

```cmake
cmake_minimum_required(VERSION 4.3)
project(example VERSION 1.0.0 LANGUAGES NONE)
find_package(besa CONFIG REQUIRED)
include(cmake/options.cmake) # Native CMake CACHE options and besa_finalize_options()

if(BUILD_SOURCE)
  besa_add_library(NAME libexample INSTALL YES)
  besa_add_directory(LIBRARY libexample ROOT src/cpp TYPE cpp)
endif()
if(BUILD_TESTING)
  add_subdirectory(test)
endif()
```

`besa_add_library(NAME libexample INSTALL YES)` is a small wrapper around CMake's
`add_library`: it sets `OUTPUT_NAME` so `libexample` builds as `libexample.a` rather than
`liblibexample.a`, creates the `example::libexample` alias, and registers the target for installation
when `INSTALL YES` (the default). `INSTALL NO` keeps the target build-only. The optional
`TYPE` argument accepts `STATIC`, `SHARED`, `MODULE`, `OBJECT`, or `INTERFACE`:
`besa_add_library(NAME libexample TYPE STATIC INSTALL YES)`. Without `TYPE`, CMake selects
`STATIC` or `SHARED` according to `BUILD_SHARED_LIBS`. Bare kinds such as `STATIC` without
`TYPE` are not accepted.

`besa_add_directory(LIBRARY libexample ROOT path TYPE cpp)` attaches a source tree to an existing
library. It recursively adds files under `path/lib/` as private sources and publishes files under
`path/include/` through a header file set and the public include path. Multiple directory trees may
be attached to one library, and a project may define any number of independent libraries. `ROOT`
is relative to the current source directory. A C++ root may also provide `module/` files;
Fortran additionally uses `mod/`. Built-in semantic language types are `c`, `cpp`, `cuda`, `hip`,
and `fortran`.

`besa_add_subdirectory(DIRECTORY path TYPE bin)` creates one executable for every
regular file directly in `path/`, without selecting source extensions or
implicitly linking any library. CMake determines the executable language from
its sources and the languages already enabled in the project. Linking is
explicit via `target_link_libraries()`; BESA does not infer it. For library
source units, a previously declared `LIBRARY` target must be specified. Library
implementations include every file recursively under `lib/` and use the declared
semantic `TYPE` to choose the source language, even for unusual extensions.
BESA does not impose any language standard; select compilers, standards and
related requirements using command-line cache options, toolchain files or
CMake presets, rather than project `CMakeLists.txt` settings.

Generators register a custom type that resolves to one built-in type:

```cmake
besa_register_subdirectory_type(
  jnum
  FUNCTION jnum_add_subdirectory
  RESOLVES_TO cpp
  GENERATED
)

besa_add_library(NAME libexample TYPE STATIC INSTALL YES)
besa_add_directory(LIBRARY libexample ROOT schema TYPE jnum)
```

BESA owns the generated prefix and the global `codegen` target. The callback receives `SOURCE_DIR`,
`BUILD_DIR`, `OUTPUT_DIR`, and `OUTPUT_TARGET_VARIABLE`; any extra `ARGS` supplied to
`besa_add_directory()` are forwarded unchanged. This lets cpdocs build `codegen` on the host and
then read the generated `include/`, `lib/`, and (for Fortran) `mod/` roots without building the target
application.

Registered features are independent by default. Use `besa_features_conflict(a b)` for a
pairwise exclusion; retain `besa_keyso_*` and `besa_set_feature_space` when precise
feature spaces are needed. BESA writes its semantic manifest inside the build tree
(`build/besa/manifest.json`) and exports both CMake and CPS package descriptions
when public targets are installed. An installation-time JSON manifest enumerates the
actual installed paths. `src/cpp/module/` is optional. Every regular file under it is registered
as a public C++ module interface; the project must select a suitable C++
standard externally via a preset, toolchain file, or CMake command line.

## Project options and test selection

As in the Nola project layout, a project declares its user-facing cache variables once in
`cmake/options.cmake`. BESA registers their metadata and resolves feature, devtool, and test-mode
selections before any targets or tests are created:

```cmake
# cmake/options.cmake
set(PROJECT_FEATURE "none" CACHE STRING "Selected project features")
besa_set_feature_variable(PROJECT_FEATURE)
set(BUILD_DEVTOOLS "none" CACHE STRING "Enabled development tools")
set(BUILD_WARNINGS "minimal" CACHE STRING "Warning policies")
option(BUILD_TESTING "Build tests" OFF)
set(TEST_MODE "commit" CACHE STRING "Test mode")
besa_test_modes_add(MODES commit)

besa_register_options(GROUP project VARIABLES PROJECT_FEATURE)
besa_register_options(GROUP build VARIABLES BUILD_DEVTOOLS BUILD_WARNINGS BUILD_TESTING TEST_MODE)
besa_finalize_options()
```

Source and test declarations use the resolved configuration. There is no second `SANITIZER`
variable or hidden build option to choose test fixtures. The example below registers tests
only when their corresponding developer tool has been selected through `BUILD_DEVTOOLS`:

```cmake
# CMakeLists.txt
include(cmake/options.cmake)
include(CTest)
foreach(DEVTOOL_NAME IN ITEMS asan ubsan)
  besa_devtools_check(OUTPUT_VARIABLE DEVTOOL_ENABLED DEVTOOLS "${DEVTOOL_NAME}")
  if(DEVTOOL_ENABLED)
    besa_test_add_directory(NAME "${DEVTOOL_NAME}" PREFIX sanitizers)
  endif()
endforeach()
```

`besa_test_add_directory()` may still express test requirements through `MODES` and `CONDITION`
when a test supports a subset of declared test modes or project features. These are predicates
on the already-resolved configuration, not independent user-facing options.
