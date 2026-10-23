# Installation and packaging

Everything registered with `INSTALL YES` (the default) is installed, exported
and described for downstream consumers without a single `install()` call in
the project. Consumers need only `find_package(<project>)` — they do not
need BESA.

## What gets installed

For a project `greet` with library `libgreet` and executable `greet-cli`,
`cmake --install build --prefix <prefix>` produces:

```text
<prefix>/
├── bin/greet-cli
├── lib/libgreet.a                                 # or .so
├── include/greet/greet.hpp                        # the unit's include/ file set
├── include/greet/version.hpp                      # the generated header
├── share/greet/modules/...                        # C++ module interfaces, if any
├── lib/cmake/greet/
│   ├── greetConfig.cmake
│   ├── greetConfigVersion.cmake                   # SameMajorVersion
│   └── greetTargets.cmake                         # exports greet::libgreet, greet::greet-cli
├── lib/cps/greet/greet.cps                        # Common Package Specification
└── share/greet/install-manifest.json
```

Destinations come from `GNUInstallDirs` (`CMAKE_INSTALL_BINDIR`,
`CMAKE_INSTALL_LIBDIR`, `CMAKE_INSTALL_INCLUDEDIR`, `CMAKE_INSTALL_DATADIR`),
so `-DCMAKE_INSTALL_LIBDIR=lib64` and friends behave as expected. The rules
are generated at [finalization](lifecycle.md#phase-4-finalize), after all
targets exist.

Per target:

- **Libraries** — `ARCHIVE`/`LIBRARY`/`RUNTIME` artifacts; every
  `INTERFACE_HEADER_SETS` file set to `include/`; every
  `INTERFACE_CXX_MODULE_SETS` file set to `share/<project>/modules/`.
  Header-only (`INTERFACE`) libraries install their header sets too.
- **Executables** — `RUNTIME` to `bin/`.

All installed targets join one export set, `<project>Targets`, with the
namespace `<project>::`, so the imported names match the in-tree aliases.

## The package configuration

`<project>Config.cmake` is generated, not templated. It contains the
`find_dependency()` calls derived from
[`besa_dependency_add()`](#declaring-dependencies), includes the targets
file, and sets `<project>_VERSION_STRING` to the resolved
[semantic version](versioning.md):

```cmake
include(CMakeFindDependencyMacro)
find_dependency(Threads)
find_dependency(MPI COMPONENTS CXX)
include("${CMAKE_CURRENT_LIST_DIR}/greetTargets.cmake")
set(greet_VERSION_STRING "1.2.3-rc.2")
```

`<project>ConfigVersion.cmake` uses `PROJECT_VERSION` with
`SameMajorVersion`: `find_package(greet 1.2)` accepts `1.4.0` and rejects
`2.0.0`.

## CPS

CMake 4.3's native `install(PACKAGE_INFO)` emits a
[Common Package Specification](https://cps-org.github.io/cps/) file from the
same export set. Build tools and package managers that read CPS get the same
targets, include directories and module directories as CMake consumers,
with all installed targets listed as `DEFAULT_TARGETS`.

## The installation manifest

`share/<project>/install-manifest.json` lists what was **actually**
installed — not a projection of declared targets — relative to the prefix:

```json
{
  "schema": "besa-installation",
  "schema_version": 1,
  "files": [
    "bin/greet-cli",
    "include/greet/greet.hpp",
    "include/greet/version.hpp",
    "lib/cmake/greet/greetConfig.cmake",
    "..."
  ]
}
```

It is written by an `install(CODE)` step after the other rules, honours
`DESTDIR`, and excludes itself. Packagers can use it to verify a build or
to produce file lists without parsing CMake's `install_manifest.txt`.

## Declaring dependencies

```cmake
besa_dependency_add(
  NAME <package>
  [KIND NORMAL|BUILD|DEV]
  [PROVIDER CMAKE|PKGCONFIG]
  [VERSION <version>]
  [COMPONENTS <component>...]
  [VISIBILITY PUBLIC|PRIVATE|INTERFACE]
  [CONDITION <feature-space>]
)
```

`besa_dependency_add()` does two things: it **finds** the package now, and
— for `KIND NORMAL` — it **records** it so the generated
`<project>Config.cmake` finds it again for consumers.

```cmake
besa_dependency_add(NAME Threads)
target_link_libraries(libgreet PRIVATE Threads::Threads)

besa_dependency_add(NAME MPI COMPONENTS CXX CONDITION mpi)
if(PROJECT_FEATURE_MPI)
  target_link_libraries(libgreet PUBLIC MPI::MPI_CXX)
endif()

besa_dependency_add(NAME zlib PROVIDER PKGCONFIG)
target_link_libraries(libgreet PRIVATE PkgConfig::BESA_PKG_ZLIB)
```

- `PROVIDER CMAKE` (default) runs `find_package(<NAME> [VERSION] REQUIRED
  [COMPONENTS ...])` and later emits a matching `find_dependency()`.
- `PROVIDER PKGCONFIG` runs `pkg_check_modules(BESA_PKG_<NAME> REQUIRED
  IMPORTED_TARGET <NAME>)`, giving you `PkgConfig::BESA_PKG_<NAME>` (name
  upper-cased, punctuation → `_`), and emits the same for consumers.
- `KIND BUILD` and `KIND DEV` find the package but do not record it: use
  them for tools and test-only dependencies that consumers should not need.
- `CONDITION` skips the dependency entirely when the feature space does not
  match, so an optional MPI build does not force MPI on consumers of the
  non-MPI build.
- `VISIBILITY` is recorded for the manifest and future use; linking is still
  done by you with the visibility you choose.

## Build-only targets

`besa_add_library(NAME libinternal INSTALL NO)` keeps a target out of the
install, the export set, the config file and the CPS description. It can
still be linked `PRIVATE` by installed targets. Linking it `PUBLIC` from an
installed target would make CMake's export step fail, exactly as it would
without BESA — the export set must be closed.

## Consuming an installed package

```cmake
cmake_minimum_required(VERSION 4.3)
project(consumer LANGUAGES CXX)
find_package(greet 1.2 CONFIG REQUIRED)
add_executable(app main.cpp)
target_link_libraries(app PRIVATE greet::libgreet)
```

```bash
cmake -S consumer -B consumer/build -DCMAKE_PREFIX_PATH=<prefix>
```

The consumer sees public include directories, header file sets, C++ module
interfaces (with a module-capable generator) and transitive dependencies.
BESA's warning and devtool flags are not part of the export, so the
consumer's own policies apply.
