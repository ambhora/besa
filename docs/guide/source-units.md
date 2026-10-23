# Libraries and source units

BESA separates two things that CMake usually conflates: **creating a target**
and **attaching source to it**. Libraries are created with
`besa_add_library()`. Source trees are attached with `besa_add_directory()`.
Any number of trees, in any mix of languages, may feed one library, and a
project may have any number of libraries.

## Creating libraries

```cmake
besa_add_library(NAME <target> [TYPE STATIC|SHARED|MODULE|OBJECT|INTERFACE] [INSTALL YES|NO])
```

`besa_add_library()` is a thin wrapper over `add_library()` that adds four
conventions:

1. **`OUTPUT_NAME`.** A target named `libfoo` builds as `libfoo.a` /
   `libfoo.so`, not `liblibfoo.a`. Name your targets the way you want the
   files to be named.
2. **A namespaced alias.** `<PROJECT_NAME>::<target>` always exists, so
   in-tree and installed consumers use the same name.
3. **Installation registry.** `INSTALL YES` (the default) registers the
   target for `make install`, the export set, the package config and the CPS
   file. `INSTALL NO` keeps it build-local.
4. **Shared policies.** Warning policies and compiler devtools selected for
   the build are applied to the target once its language is known.

`TYPE` is optional. Without it, CMake chooses `STATIC` or `SHARED` from
`BUILD_SHARED_LIBS`, exactly as `add_library(name)` does. Bare kinds such as
`besa_add_library(NAME libfoo STATIC)` are rejected; write `TYPE STATIC`.

```cmake
besa_add_library(NAME libone TYPE STATIC)                 # installed
besa_add_library(NAME libtwo TYPE SHARED)                 # installed
besa_add_library(NAME libinternal TYPE STATIC INSTALL NO) # build-only
besa_add_library(NAME libheaders TYPE INTERFACE)          # header-only, installed
besa_add_library(NAME libdefault)                         # follows BUILD_SHARED_LIBS
```

All BESA libraries are peers. There is no implied `lib<project>` target and
nothing special about the first library you declare.

## Attaching source units

```cmake
besa_add_directory(LIBRARY <target> ROOT <path> TYPE <type> [CONDITION <space>] [ARGS ...])
```

`ROOT` is relative to the current source directory. BESA discovers the
[conventional subdirectories](../getting-started/layout.md#a-source-unit)
beneath it and attaches them to `LIBRARY`:

- `include/**` → `target_sources(... PUBLIC FILE_SET HEADERS BASE_DIRS include ...)`
  plus `$<BUILD_INTERFACE:…/include>` / `$<INSTALL_INTERFACE:include>` on the
  include path. For an `INTERFACE` library the visibility is `INTERFACE`.
- `lib/**` → `target_sources(... PRIVATE ...)`, every file forced to the
  unit's language with the `LANGUAGE` source property.
- `module/**` (`cpp` only) → `target_sources(... PUBLIC FILE_SET CXX_MODULES BASE_DIRS module ...)`.
- `mod/**` (`fortran` only) → `PRIVATE` sources.

`LIBRARY` must be a writable local library target created earlier — not an
alias, not an imported target, not an executable. Attaching compiled sources
to an `INTERFACE` library is an error.

### Several units, one library

Units are a way to organize source, not a unit of linkage. Spread one
library over as many trees as make sense:

```cmake
besa_add_library(NAME libcore TYPE STATIC)
besa_add_directory(LIBRARY libcore ROOT core TYPE cpp)
besa_add_directory(LIBRARY libcore ROOT io   TYPE cpp)
besa_add_directory(LIBRARY libcore ROOT cbindings TYPE c)
```

Each `ROOT` contributes its own `include/` to the public include path, so
headers from different units may use different top-level namespaces or share
one.

### Feature-selected units

`CONDITION` names a [feature space](feature-spaces.md). The unit is attached
only when the resolved feature set matches:

```cmake
besa_add_directory(LIBRARY libcore ROOT host   TYPE cpp  CONDITION host)
besa_add_directory(LIBRARY libcore ROOT device TYPE cuda CONDITION gpu)
```

Every declared feature is also a feature space containing just that feature,
so `CONDITION gpu` works without further declarations. Conditions use
*subset* matching: `CONDITION gpu` is satisfied whenever `gpu` is among the
enabled features, whatever else is enabled alongside it.

Note that the feature (`gpu`) and the language (`cuda`) are independent. A
feature is a capability the project offers; a type is the language of one
tree that happens to implement it. The `languages` fixture in the BESA repository exists to make exactly this
point: both its `host` and `gpu` units are `TYPE cpp`.

### Languages

`besa_add_directory()` calls `enable_language()` for the unit's type the
first time that type is used. Starting the project with `LANGUAGES NONE` and
letting units enable what they need keeps configure time down and keeps the
manifest honest about which languages the project really uses.

BESA never sets a language standard. `CMAKE_CXX_STANDARD`,
`CMAKE_CUDA_ARCHITECTURES` and similar belong in a preset, a toolchain file
or on the command line. The manifest records whichever standard was in
effect.

### C++ modules

Files under `module/` in a `cpp` unit are registered as a public
`CXX_MODULES` file set. Module interface units are installed to
`share/<project>/modules/` and exported through the `CXX_MODULES_DIRECTORY`
of the package, so downstream projects can import them. Select a standard
that supports modules (`-DCMAKE_CXX_STANDARD=20` or later) and a generator
that supports module scanning.

## Standalone units: `besa_add_subdirectory()`

```cmake
besa_add_subdirectory(DIRECTORY <path> TYPE <type> [LIBRARY <target>] [CONDITION <space>] [ARGS ...])
```

`besa_add_directory()` is the library-oriented front end; it validates that
`LIBRARY` is a suitable library and then calls `besa_add_subdirectory()`.
Use `besa_add_subdirectory()` directly for the one type that has no library:
`bin`.

```cmake
besa_add_subdirectory(DIRECTORY bin TYPE bin)
target_link_libraries(greet-cli PRIVATE greet::libgreet)
```

For every regular file directly inside `bin/`, BESA creates one executable
named after the file (without its last extension), registers it for
installation, and applies the warning/devtool policies. It does **not**
enable a language, guess a language from the extension, or link anything.
`TYPE bin` says only "these files are programs"; what they are programs *in*
is left to CMake's normal inference from the enabled languages.

For every other type, `LIBRARY` is required, and `besa_add_directory()` is
the clearer spelling.

## Executables by hand

```cmake
besa_add_executable(NAME <name> [INSTALL <bool>] [SOURCES <files>...] [LINK_LIBRARIES <targets>...])
```

When the one-file-per-program convention does not fit, declare the
executable explicitly. `INSTALL` defaults to `TRUE`; `LINK_LIBRARIES` are
linked `PRIVATE`. This is the same command the `bin` type and the test
discovery use internally, so hand-declared executables receive the same
policies.

## Public header hygiene

When the `surrogate` devtool is selected and `BUILD_TESTING` is on, BESA
automatically registers a `surrogate.<library>.t` test for every non-interface
library created with `besa_add_library()`. The test compiles each public
header in its own translation unit, in the language declared for the unit
that owns it, so a header that forgets an include or depends on being
included after another one is caught. See
[Developer tools](devtools.md#surrogate-public-header-checks).

## Everything is still a CMake target

BESA targets are plain CMake targets. Once created you may call any
`target_*()` command on them — `target_link_libraries()`,
`target_compile_definitions()`, `target_precompile_headers()` — and they
will be exported and installed accordingly. BESA records the result; it
does not stand between you and CMake.
