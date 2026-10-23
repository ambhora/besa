# Command reference

Every public BESA command, grouped by purpose. The **Phase** column says
when a command may be called (see
[How a BESA project is configured](../guide/lifecycle.md)):

- **open** — after `find_package(besa)`, before `besa_finalize_options()`
- **complete** — after `besa_finalize_options()`
- **any** — no restriction

All public commands take named arguments. Unknown arguments and missing
required values are fatal errors with the command name in the message.

## Configuration lifecycle

### `besa_finalize_options`

```cmake
besa_finalize_options()
```

Phase: open → complete. Resolves features, devtools, test modes, warnings
and release metadata; validates them; publishes the resolved state; prints
the configuration summary; freezes the configuration; schedules project
finalization. Must be called exactly once, from a directory scope, after
all declarations and before any target. Also forces
`CMAKE_EXPORT_COMPILE_COMMANDS=ON`.

### `besa_configure_complete`

```cmake
besa_configure_complete()
```

Alias for `besa_finalize_options()`.

### `besa_register_options`

```cmake
besa_register_options(GROUP <group> VARIABLES <cache-variable>...)
```

Phase: open. Records existing cache variables (type, help string, allowed
`STRINGS`, value) under a group name for the manifest. Each variable may be
registered once; non-cache variables are rejected.

### `besa_workspace_initialize`

```cmake
besa_workspace_initialize()
```

Phase: any. Creates `build/besa/{codegen,docs,configure_cache}` and
publishes `BESA_CODEGEN_DIRECTORY`, `BESA_DOCS_DIRECTORY`,
`BESA_CONFIGURE_CACHE_DIRECTORY`, `BESA_BUILD_DIRECTORY`. Called by
`besa_finalize_options()`; projects rarely need it.

## Features

### `besa_add_feature`

```cmake
besa_add_feature(<name>)
```

Phase: open. Declares one atomic feature and a feature space of the same
name containing only it. Names: `[A-Za-z0-9][A-Za-z0-9_.+-]*`. Duplicates
are errors.

### `besa_set_feature_variable`

```cmake
besa_set_feature_variable(<cache-variable>)
```

Phase: open. Names the cache variable holding the user's feature selection
(a CMake list; `none` and empty entries ignored). Without it, BESA reads
`PROJECT_FEATURES` if defined, else the project space default.

### `besa_features_conflict`

```cmake
besa_features_conflict(<first> <second>)
```

Phase: open. Declares two distinct declared features mutually exclusive.

### `besa_set_feature_space`

```cmake
besa_set_feature_space(<space> [DEFAULT <singleton-space>])
```

Phase: open. Makes `<space>` the project feature space: the selection must
be exactly one of its members. `DEFAULT` must have exactly one member that
is in `<space>`. Without `DEFAULT`, the empty set if present, else the first
member.

## Feature spaces (Keyso)

All phase: open. `<feature>` arguments must be declared features; at least
one is required.

### `besa_keyso_all_of`

```cmake
besa_keyso_all_of(<space> <feature>...)
```

One member: the set of all listed features.

### `besa_keyso_one_of`

```cmake
besa_keyso_one_of(<space> <feature>...)
```

One singleton member per listed feature.

### `besa_keyso_zero_or_one`

```cmake
besa_keyso_zero_or_one(<space> <feature>...)
```

The empty set plus one singleton member per listed feature.

### `besa_keyso_any_of`

```cmake
besa_keyso_any_of(<space> <feature>...)
```

Every non-empty subset of the listed features.

### `besa_keyso_create_feature_space`

```cmake
besa_keyso_create_feature_space(<space> UNION|INTERSECTION|SETMINUS|PRODUCT <space>...)
```

Builds a space from existing spaces. `UNION`: all members. `INTERSECTION`:
members in every operand. `SETMINUS`: members of the first operand absent
from all others. `PRODUCT`: unions of one member chosen from each operand.

## Targets and source units

### `besa_add_library`

```cmake
besa_add_library(NAME <target> [TYPE STATIC|SHARED|MODULE|OBJECT|INTERFACE] [INSTALL YES|NO])
```

Phase: complete. Creates a library, the alias `<PROJECT_NAME>::<target>`,
sets `OUTPUT_NAME` to strip a leading `lib`, applies warning and devtool
policies (deferred), and registers it for installation unless `INSTALL NO`.
Without `TYPE`, `BUILD_SHARED_LIBS` decides. With the `surrogate` devtool
and `BUILD_TESTING`, non-interface libraries get a `surrogate.<target>.t`
test.

### `besa_add_executable`

```cmake
besa_add_executable(NAME <name> [INSTALL <bool>] [SOURCES <file>...] [LINK_LIBRARIES <target>...])
```

Phase: complete. Creates an executable, links `LINK_LIBRARIES` privately,
applies policies, registers for installation when `INSTALL` is true (the
default).

### `besa_add_directory`

```cmake
besa_add_directory(LIBRARY <target> ROOT <path> TYPE <type> [CONDITION <space>] [ARGS <arg>...])
```

Phase: complete. Macro. Attaches the source unit at `ROOT` (relative to the
current source directory) to `LIBRARY`, which must be a local, non-alias,
non-imported library target. `TYPE` is a built-in library type (`c`, `cpp`,
`cuda`, `hip`, `fortran`) or a registered generated type; `bin` is not
allowed. Enables the type's language. `CONDITION` is matched by subset
against the enabled features. `ARGS` are forwarded to a generated type's
callback.

### `besa_add_subdirectory`

```cmake
besa_add_subdirectory(DIRECTORY <path> TYPE <type> [LIBRARY <target>] [CONDITION <space>] [ARGS <arg>...])
```

Phase: complete. Macro. The general form behind `besa_add_directory()`.
With `TYPE bin`, creates one executable per regular file in `DIRECTORY`
(name = file name without last extension) and needs no `LIBRARY`. For any
other type `LIBRARY` is required.

### `besa_register_subdirectory_type`

```cmake
besa_register_subdirectory_type(<type> GENERATED FUNCTION <command> RESOLVES_TO <builtin-type>)
```

Phase: open. Registers a generated unit type. `FUNCTION` must exist and is
called with `SOURCE_DIR`, `BUILD_DIR`, `OUTPUT_DIR`, `OUTPUT_TARGET_VARIABLE`
plus forwarded `ARGS`. `RESOLVES_TO` must be a built-in library type.
`GENERATED` is required.

### `besa_dependency_add`

```cmake
besa_dependency_add(NAME <package> [KIND NORMAL|BUILD|DEV] [PROVIDER CMAKE|PKGCONFIG]
                    [VERSION <version>] [COMPONENTS <component>...]
                    [VISIBILITY PUBLIC|PRIVATE|INTERFACE] [CONDITION <space>])
```

Phase: complete. Finds the package now (`find_package(... REQUIRED)` or
`pkg_check_modules(BESA_PKG_<NAME> REQUIRED IMPORTED_TARGET ...)`) and, for
`KIND NORMAL` (default), records it for the generated package config's
`find_dependency()` calls. Skipped entirely when `CONDITION` does not match.
Defaults: `NORMAL`, `CMAKE`, `PRIVATE`.

## Tests

### `besa_test_add_directory`

```cmake
besa_test_add_directory(NAME <dir> [PREFIX <prefix>] [TARGET_LIST <target>...] [LABELS <label>...]
                        [CMDLINE <arg>...] [CONDITION <space>] [MODES <mode>...]
                        [DEVTOOLS <devtool>...] [COVERAGE_GROUP <group>])
```

Phase: complete. Recursively discovers `*.t.{c,cc,cpp,cxx,cu}` under `<dir>`
(relative to the current source directory, must exist). Each becomes an
uninstalled executable linked to `TARGET_LIST` and a CTest test named
`<prefix>.<path.with.dots>` run with `CMDLINE`. `.fail.` → `WILL_FAIL`,
`.disabled.` → `DISABLED`. A directory with the test's stem supplies extra
sources. Skipped unless `CONDITION`, `MODES` (any-of) and `DEVTOOLS`
(any-of) all match. With the `coverage` devtool, `COVERAGE_GROUP` assigns
the tests to a report group.

### `besa_compile_test_add_directory`

```cmake
besa_compile_test_add_directory(NAME <dir> [PREFIX <prefix>] [TARGET_LIST <target>...] [LABELS <label>...]
                                [CONDITION <space>] [MODES <mode>...] [DEVTOOLS <devtool>...])
```

Phase: complete. Same discovery, naming, suffixes and selection; each test
is an `EXCLUDE_FROM_ALL` executable whose CTest test builds it. `.fail.`
means "must not compile".

### `besa_test_modes_add`

```cmake
besa_test_modes_add(MODES <mode>...)
```

Phase: open. Declares test mode names (no leading `~`; no duplicates).

### `besa_test_modes_default`

```cmake
besa_test_modes_default(MODES <mode>...)
```

Phase: open. Selects declared modes enabled when `TEST_MODE` is unset.

### `besa_test_modes_check`

```cmake
besa_test_modes_check(OUTPUT_VARIABLE <var> [MODES <mode>...])
```

Phase: complete. `TRUE` if any listed declared mode is enabled; `TRUE` with
no list. `~` and unknown names are errors.

### `besa_register_test_mode_constraint`

```cmake
besa_register_test_mode_constraint(FUNCTION <command>)
```

Phase: open. Registers a callback invoked at finalization with
`OUTPUT_VARIABLE`, `ERROR_VARIABLE` and `MODES <enabled>...`; it must set
the output to a boolean in `PARENT_SCOPE` and may set an error message.

### `besa_test_mode_constraint_arguments_parse`

```cmake
besa_test_mode_constraint_arguments_parse(PREFIX <prefix> ARGUMENTS ${ARGN})
```

Phase: any. Inside a constraint callback, exposes `<prefix>_MODES`,
`<prefix>_OUTPUT_VARIABLE`, `<prefix>_ERROR_VARIABLE`.

## Developer tools

### `besa_devtools_check`

```cmake
besa_devtools_check(OUTPUT_VARIABLE <var> [DEVTOOLS <devtool>...])
```

Phase: complete. `TRUE` if any listed devtool is enabled; `TRUE` with no
list. Unknown or repeated names are errors.

### `besa_register_devtool_constraint`

```cmake
besa_register_devtool_constraint(FUNCTION <command>)
```

Phase: open. Registers a callback invoked at finalization with
`OUTPUT_VARIABLE`, `ERROR_VARIABLE` and `DEVTOOLS <enabled>...`.

### `besa_devtool_constraint_arguments_parse`

```cmake
besa_devtool_constraint_arguments_parse(PREFIX <prefix> ARGUMENTS ${ARGN})
```

Phase: any. Inside a constraint callback, exposes `<prefix>_DEVTOOLS`,
`<prefix>_OUTPUT_VARIABLE`, `<prefix>_ERROR_VARIABLE`.

### `besa_surrogate_check`

```cmake
besa_surrogate_check(TARGET <library> [EXPECT PASS|FAIL] [LABELS <label>...])
```

Phase: complete. Registers a deferred check that compiles every public
header of `TARGET` in its own translation unit, as the CTest test
`surrogate.<target>.t` (building target of the same name). `EXPECT FAIL`
sets `WILL_FAIL`. Default labels: `instrumentation surrogate`. Called
automatically for BESA libraries when the `surrogate` devtool is on.

### `besa_add_clang_format`

```cmake
besa_add_clang_format(NAME <test> [LABELS <label>...])
```

Phase: complete. Adds a CTest test running `clang-format --dry-run -Werror
--style=file` over the source tree. Requires `clang-format`. Called
automatically as `instrumentation.format.t` by the `format` devtool.

### `besa_add_clang_tidy`

```cmake
besa_add_clang_tidy(NAME <test> [LABELS <label>...] [ARGUMENTS <arg>...])
```

Phase: complete. Adds a CTest test running `run-clang-tidy` against the
compilation database; `ARGUMENTS` are appended verbatim. Requires
`clang-tidy`, `run-clang-tidy` and `CMAKE_EXPORT_COMPILE_COMMANDS`. Called
automatically as `instrumentation.linting.t` by the `linting` devtool.

## Documentation

### `besa_add_cpdocs_docs`

```cmake
besa_add_cpdocs_docs(NAME <target> CONFIG <file> [OUTPUT_DIRECTORY <dir>] [VERSIONS_NAME <target>]
                     [VERSIONS_OUTPUT_DIRECTORY <dir>] [INSTALL_DIRECTORY <dir>]
                     [VERSIONS_INSTALL_DIRECTORY <dir>] [NO_INSTALL])
```

Phase: complete. Creates `<NAME>` (current API) and `<VERSIONS_NAME>`
(default `<NAME>.versions`) targets invoking `cpdocs`; installs their
outputs unless `NO_INSTALL`. Requires `cpdocs`.

### `besa_add_user_docs`

```cmake
besa_add_user_docs(NAME <target> PROPERDOCS_CONFIG <file> CPDOCS_CONFIG <file>
                   [OUTPUT_DIRECTORY <dir>] [INSTALL_DIRECTORY <dir>])
```

Phase: complete. Creates `<NAME>.api`, `<NAME>.api.versions` and `<NAME>`
(ProperDocs site) targets; installs the site. Requires `properdocs` and
`cpdocs`.
