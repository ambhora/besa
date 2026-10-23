# Project options

A BESA project exposes its configuration through **ordinary CMake cache
variables**. There is no BESA-specific option syntax: users pass `-D` flags,
presets, or a `CMakeCache.txt` exactly as they would for any CMake project.
What BESA adds is a fixed set of variable *names* whose values it resolves
and validates, and a registry so tools can discover them.

## The options file

Keep every user-facing variable in one file, conventionally
`cmake/options.cmake`, and end it with `besa_finalize_options()`:

```cmake
# cmake/options.cmake
set(PROJECT_FEATURE "none" CACHE STRING "Selected project features")
besa_set_feature_variable(PROJECT_FEATURE)
besa_add_feature(mpi)
besa_add_feature(gpu)

set(BUILD_DEVTOOLS "none" CACHE STRING "Enabled development tools")
set(BUILD_WARNINGS "minimal" CACHE STRING "Warning policies")
option(BUILD_TESTING "Build tests" OFF)
set(TEST_MODE "commit" CACHE STRING "Test mode")
besa_test_modes_add(MODES commit merge)
besa_test_modes_default(MODES commit)

besa_register_options(GROUP project VARIABLES PROJECT_FEATURE)
besa_register_options(GROUP build VARIABLES BUILD_DEVTOOLS BUILD_WARNINGS BUILD_TESTING TEST_MODE)
besa_finalize_options()
```

Include it from `CMakeLists.txt` right after `find_package(besa)`. Everything
that follows can rely on a validated configuration.

!!! tip "Why declare the variables yourself?"
    BESA could create `BUILD_DEVTOOLS` and friends for you — and it does, with
    sensible defaults, if you leave them undefined. Declaring them in the
    project is still worthwhile: you choose the defaults and help strings,
    you can add `STRINGS` properties so `cmake-gui` and `ccmake` offer the
    valid values, and the manifest records them as *this project's* options.

## Variables BESA resolves

These are read during `besa_finalize_options()`. Each is a semicolon-separated
CMake list unless noted.

### `PROJECT_FEATURE` (or any name you choose)

The enabled [features](features.md). Connect a variable with
`besa_set_feature_variable(<name>)`. Values are feature names; the literal
`none` and empty entries are ignored, so `-DPROJECT_FEATURE=none` means "no
features".

If no variable is connected, BESA falls back to `PROJECT_FEATURES` for
compatibility with older projects, and otherwise to the default of the
project feature space.

### `BUILD_DEVTOOLS`

Default `none`. Zero or more of `format`, `linting`, `coverage`,
`surrogate`, `asan`, `lsan`, `ubsan`. `none` cannot be combined with other
values. The catalog is owned by BESA; projects select from it but do not
extend it. See [Developer tools](devtools.md).

### `BUILD_WARNINGS`

Default `minimal`. At most one of the levels `minimal`, `extra`,
`everything`, optionally combined with `werror`; or `none`. See
[Warning policies](warnings.md).

### `BUILD_TESTING`

The standard CTest switch. BESA consults it when deciding whether to
register devtool-driven tests (format, linting, coverage reports, surrogate
checks). Your project decides whether to call `besa_test_add_directory()`
under it, exactly as with plain CMake.

### `TEST_MODE` and `TEST_MODES`

`TEST_MODE` selects exactly one declared [test mode](test-modes.md), or
`none`. `TEST_MODES` is an override list applied on top: `merge` adds a
mode, `~merge` removes one. The common case is a single `TEST_MODE` with a
project default.

### `RELEASE_TYPE`, `RELEASE_REVISION`, `PKGBUILDER_ID`, `PKGBUILDER_REVISION`

Release channel and packaging provenance baked into the generated version
header. Defaults: `dev`, `1`, `vanilla`, `1`. See
[Versions and release metadata](versioning.md).

### `BUILD_SHARED_LIBS`

Not resolved by BESA, but honoured: libraries created without `TYPE` follow
it, just as `add_library()` does.

## Registering options for tools

```cmake
besa_register_options(GROUP <group> VARIABLES <variable>...)
```

Registration has no effect on the build. It records, for each variable, its
group, cache type, help string, allowed `STRINGS` and current value in the
[manifest](../reference/manifest.md). cpdocs uses this to document the
project's configuration knobs; CI generators and packagers can use it to
enumerate build variants.

Only existing cache variables may be registered, and each at most once.
Group names are free-form; `project` and `build` are the conventional pair.

Registering a variable BESA does not know about is fine — a project-specific
`USE_SYSTEM_ZLIB` can be listed alongside `BUILD_DEVTOOLS`.

## Reading the resolved configuration

After `besa_finalize_options()`, the resolved state is available in several
forms. Prefer the query commands in project code; the variables are handy in
`if()` conditions and for scripts.

| Query | Resolved form |
| --- | --- |
| `besa_devtools_check(OUTPUT_VARIABLE v DEVTOOLS asan ubsan)` | `BUILD_DEVTOOLS_ASAN`, `BUILD_DEVTOOLS_UBSAN`, … (booleans) |
| `besa_test_modes_check(OUTPUT_VARIABLE v MODES merge)` | `PROJECT_TEST_MODE_MERGE`, … (booleans); `BESA_ENABLED_TEST_MODES` (list) |
| `CONDITION <space>` on units, tests, dependencies | `PROJECT_FEATURE_GPU`, … (booleans); `BESA_ENABLED_FEATURES` (list) |
| — | `BUILD_WARNINGS_WERROR`, … (booleans); `BESA_ENABLED_WARNINGS` (list) |
| — | `PROJECT_SEMVER` (string) |

Names are upper-cased with non-alphanumeric characters replaced by `_`, so
the test mode `ci-merge` becomes `PROJECT_TEST_MODE_CI_MERGE`.

Both check commands use **any-of** semantics: the output is `TRUE` when at
least one of the listed names is enabled. With no list they return `TRUE`.
Unknown names are errors, which is what makes the queries safer than
`if("asan" IN_LIST BUILD_DEVTOOLS)`: a typo fails configuration instead of
silently disabling a test.

## Custom validation

Sometimes the valid combinations of *devtools* or *test modes* depend on the
project — a mode that only makes sense with coverage, say. Register a
constraint callback before finalization:

```cmake
function(myproject_check_devtools)
  besa_devtool_constraint_arguments_parse(PREFIX ARG ARGUMENTS ${ARGN})
  if("coverage" IN_LIST ARG_DEVTOOLS AND "asan" IN_LIST ARG_DEVTOOLS)
    set(${ARG_OUTPUT_VARIABLE} FALSE PARENT_SCOPE)
    set(${ARG_ERROR_VARIABLE} "coverage and asan cannot be combined in this project" PARENT_SCOPE)
    return()
  endif()
  set(${ARG_OUTPUT_VARIABLE} TRUE PARENT_SCOPE)
endfunction()
besa_register_devtool_constraint(FUNCTION myproject_check_devtools)
```

`besa_register_test_mode_constraint()` and
`besa_test_mode_constraint_arguments_parse()` work the same way with
`ARG_MODES`. Constraints run during `besa_finalize_options()`; a rejected
set fails configuration with your message.

For *features*, validation is expressed declaratively instead — with
`besa_features_conflict()` or a [feature space](feature-spaces.md) — so that
the manifest can describe the valid configurations without running CMake.

## The configuration summary

Every configure run ends the frozen phase by printing what it resolved:

```text
-- myproject configuration:
--   Features          : gpu, mpi
--   Devtools          : asan, ubsan
--   Warning policy    : extra, werror
--   Test modes        : commit
--   Build testing     : ON
--   Release type      : dev
--   Release revision  : 1
--   Package builder   : vanilla
--   Package revision  : 1
--   Version           : dev.main.3caacb0
```

If a build behaves unexpectedly, this block is the first thing to read.
