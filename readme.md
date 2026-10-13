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
when `INSTALL YES` (the default). `INSTALL NO` keeps the target build-only. The library kind
is optional: omitting it follows CMake's `BUILD_SHARED_LIBS` default (STATIC when OFF, SHARED when
ON). For an explicit kind, use CMake-style `STATIC`, `SHARED`, `MODULE`, `OBJECT`, or `INTERFACE`
without a `TYPE` keyword, for example `besa_add_library(NAME libexample STATIC INSTALL YES)`.
`TYPE STATIC` is not supported.

`besa_add_directory(LIBRARY libexample ROOT path TYPE cpp)` attaches a source tree to an existing
library. It recursively adds files under `path/lib/` as private sources and publishes files under
`path/include/` through a header file set and the public include path. Multiple directory trees may
be attached to one library, and a project may define any number of independent libraries. `ROOT`
is relative to the current source directory. A C++ root may also provide `module/*.cppm`;
Fortran additionally uses `mod/`. Built-in semantic language types are `c`, `cpp`, `cuda`, `hip`,
and `fortran`.

`besa_add_subdirectory(DIRECTORY path TYPE bin)` creates top-level C/C++ executables.
For library source units, a previously declared `LIBRARY` target must be specified.

Generators register a custom type that resolves to one built-in type:

```cmake
besa_register_subdirectory_type(
  jnum
  FUNCTION jnum_add_subdirectory
  RESOLVES_TO cpp
  GENERATED
)

besa_add_library(NAME libexample STATIC INSTALL YES)
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
actual installed paths. `src/cpp/module/*.cppm` files are optional and automatically
attached to the existing library as public C++ module interfaces.
