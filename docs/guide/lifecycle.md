# How a BESA project is configured

Every ordering rule in BESA follows from one idea: **a project's configuration
is declared, then frozen, then consumed.** Once you see the three phases,
every "must be called before/after `besa_finalize_options()`" message in the
reference is predictable.

## The three phases

```text
find_package(besa)
        │
        ▼
┌─────────────────────────────────────────────────────┐
│ 1. OPEN — declare the configuration vocabulary       │
│    besa_add_feature(), besa_keyso_*(),               │
│    besa_set_feature_space(), besa_features_conflict()│
│    besa_test_modes_add(), besa_test_modes_default()  │
│    besa_register_subdirectory_type()                 │
│    besa_register_options()                           │
│    besa_register_devtool_constraint()                │
│    besa_register_test_mode_constraint()              │
└─────────────────────────────────────────────────────┘
        │
        ▼  besa_finalize_options()
┌─────────────────────────────────────────────────────┐
│ 2. FROZEN — resolve and validate                     │
│    features · devtools · test modes · warnings       │
│    version/release metadata · configuration summary  │
└─────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────┐
│ 3. COMPLETE — build the project model                │
│    besa_add_library(), besa_add_directory(), …       │
│    besa_test_add_directory(), besa_dependency_add()  │
│    besa_devtools_check(), besa_test_modes_check()    │
└─────────────────────────────────────────────────────┘
        │
        ▼  end of the top-level directory (deferred)
┌─────────────────────────────────────────────────────┐
│ 4. FINALIZE — emit outputs                           │
│    generated headers · manifest.json · cpdocs files  │
│    devtool tests · install/export rules              │
└─────────────────────────────────────────────────────┘
```

### Phase 1: open

Between `find_package(besa)` and `besa_finalize_options()` the
configuration is *open*. You declare what exists: which features the project
has, which test modes it defines, which option variables users may set,
which generated unit types are available. Nothing is resolved yet, and
nothing is built. BESA records the declarations in global properties.

Commands that belong here fail with

```text
configuration has already been frozen by besa_finalize_options()
```

if they are called later.

### Phase 2: frozen

`besa_finalize_options()` does the work in a fixed order:

1. Initializes the [workspace](../getting-started/layout.md#besas-own-files-in-the-build-tree)
   under `build/besa/`.
2. If cpdocs supplied a feature set file, applies it to the feature variable.
3. Resolves the enabled **features** from the feature variable, checks every
   name is declared, checks the set against the project feature space, and
   checks declared conflicts.
4. Resolves **devtools** from `BUILD_DEVTOOLS`, validates the names, then
   runs every registered devtool constraint.
5. Resolves **test modes** from the declared defaults, `TEST_MODE` and
   `TEST_MODES`, then runs every registered test-mode constraint.
6. Resolves **warning policies** from `BUILD_WARNINGS`.
7. Publishes the results as internal cache variables (`PROJECT_FEATURE_<NAME>`,
   `BUILD_DEVTOOLS_<NAME>`, `PROJECT_TEST_MODE_<NAME>`, …; see
   [Cache variables](../reference/variables.md)).
8. Resolves `RELEASE_TYPE` and friends and writes `<project>/version.hpp`
   into the codegen workspace.
9. Turns `CMAKE_EXPORT_COMPILE_COMMANDS` on, so tooling such as cpdocs and
   clang-tidy always has a compilation database.
10. Prints the configuration summary and marks the configuration **complete**.
11. Schedules phase 4 with `cmake_language(DEFER)` on the top-level source
    directory.

Any failure here is a `FATAL_ERROR` that names the rule that rejected the
input — `unknown feature 'gamma'`, `feature set 'alpha, beta' is not allowed
by project feature space 'supported'`, `unknown devtool 'valgrind'. Allowed
values are: …`.

`besa_finalize_options()` is a macro and must be called from a directory
scope. Calling it inside a function would hide the published variables from
the rest of the project. `besa_configure_complete()` is an alias for projects
that prefer that name.

### Phase 3: complete

With the configuration frozen, the model-building commands become available.
They may read the resolved configuration but can no longer change it:

- `besa_add_library()`, `besa_add_executable()`
- `besa_add_directory()`, `besa_add_subdirectory()`
- `besa_test_add_directory()`, `besa_compile_test_add_directory()`
- `besa_dependency_add()`
- `besa_devtools_check()`, `besa_test_modes_check()`
- `besa_surrogate_check()`, `besa_add_clang_format()`, `besa_add_clang_tidy()`
- `besa_add_cpdocs_docs()`, `besa_add_user_docs()`

Calling them earlier fails with

```text
besa_finalize_options() must be called before this function
```

Conditional declarations use the resolved state directly:

```cmake
besa_add_directory(LIBRARY libcore ROOT gpu TYPE cuda CONDITION gpu)

besa_devtools_check(OUTPUT_VARIABLE WITH_ASAN DEVTOOLS asan)
if(WITH_ASAN)
  besa_test_add_directory(NAME asan-tests PREFIX asan)
endif()
```

There is never a second, project-invented switch (`-DENABLE_ASAN_TESTS=ON`)
that could drift out of sync with the real selection.

### Phase 4: finalize

At the end of the top-level `CMakeLists.txt`, after every subdirectory has
been processed, BESA runs its finalizers in dependency order:

1. **Codegen** — attaches generated include roots (the version header) to
   every BESA library and installs them.
2. **Manifest** — writes `build/besa/manifest.json`.
3. **cpdocs** — writes the feature-set and manifest files cpdocs asked for,
   and creates the `besa.cpdocs` target.
4. **Devtools** — registers the format, linting and coverage CTest tests.
5. **Package** — emits `install()` rules, the `<Project>Targets` export, the
   `<Project>Config.cmake`, the CPS description and the installation
   manifest for every target that was registered for installation.

Because this runs deferred, you can declare libraries and units in any order
and across any number of `add_subdirectory()` calls; the package sees all of
them.

## Why not resolve options lazily?

Two reasons.

**Diagnostics.** Validating the whole configuration at one point means an
invalid combination is reported once, with the complete picture, before a
single target exists. Lazy validation reports whichever target happened to
notice first.

**One source of truth.** Tools downstream of CMake — documentation
generators, CI matrices, packagers — need to know what the project's options
*are*, not just what one configure run selected. Freezing the vocabulary
before anything consumes it is what makes the manifest trustworthy.

## A note on language enabling

`project(... LANGUAGES NONE)` is the recommended starting point. Languages
are enabled by `besa_add_directory()` when a unit of that type is attached.
This is why the directory-attaching commands are macros: `enable_language()`
must execute in the calling directory scope.

Compiler-dependent policies — warning flags, sanitizer flags — are therefore
applied to libraries *deferred*, at the end of the top-level directory, once
the languages are known. Executables get them immediately because an
executable always has sources. In practice you will not notice the
difference; it only matters if you inspect target properties right after
`besa_add_library()`.
