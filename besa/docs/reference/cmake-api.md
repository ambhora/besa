<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# CMake API reference

All public BESA functions use named arguments. Positional calling conventions are reserved for BESA
implementation helpers.

## Configuration

### `besa_features_add(FEATURES ...)`
Declares the complete set of feature names understood by the project.

### `besa_features_default(FEATURES ...)`
Declares features enabled before `PROJECT_FEATURES` overrides are applied.

### `besa_register_feature_constraint(FUNCTION name)`
Registers a project callback evaluated against the resolved feature set.

### `besa_feature_constraint_arguments_parse(PREFIX name ARGUMENTS ...)`
Parses the callback contract `OUTPUT_VARIABLE`, `ERROR_VARIABLE`, and `FEATURES`.

### `besa_register_devtool_constraint(FUNCTION name)`
Registers a project callback evaluated against the resolved BESA devtool set.

### `besa_devtool_constraint_arguments_parse(PREFIX name ARGUMENTS ...)`
Parses the callback contract `OUTPUT_VARIABLE`, `ERROR_VARIABLE`, and `DEVTOOLS`.

### `besa_test_modes_add(MODES ...)`
Declares the complete set of project-defined test-mode names.

### `besa_test_modes_default(MODES ...)`
Declares the test modes enabled before `TEST_MODES` overrides are applied.

### `besa_register_test_mode_constraint(FUNCTION name)`
Registers a project callback evaluated against the resolved test-mode set.

### `besa_test_mode_constraint_arguments_parse(PREFIX name ARGUMENTS ...)`
Parses the callback contract `OUTPUT_VARIABLE`, `ERROR_VARIABLE`, and `MODES`.

### `besa_test_modes_check(OUTPUT_VARIABLE variable [MODES ...])`
Returns true when at least one listed supported mode is enabled. Omitting `MODES` returns true. This
is intended for manually registered test targets/subtrees which cannot use BESA test discovery.

### `besa_selector_arguments_parse(PREFIX name ARGUMENTS ...)`
Parses a custom selector callback contract: `OUTPUT_VARIABLE`, `ERROR_VARIABLE`, `NAME`, and
`FEATURES`.

### `besa_configure_complete()`
Resolves features, devtools, test modes, and warning policies; runs registered constraints; enables
`toolchain-*` languages; activates compiler-dependent devtools; resolves release versioning; freezes
configuration; and schedules final package/instrumentation work.

## Dependencies

### `besa_dependency_add(...)`

```cmake
besa_dependency_add(
  NAME name
  [VERSION version]
  [KIND NORMAL|BUILD|DEV]
  [PROVIDER CMAKE|PKGCONFIG]
  [VISIBILITY PUBLIC|PRIVATE|INTERFACE]
  [COMPONENTS ...]
  [WHEN ANY_OF|ALL_OF|REGEX|FUNCTION ...]
)
```

Defaults: `KIND NORMAL`, `PROVIDER CMAKE`, `VISIBILITY PRIVATE`.

## Project structure

### `besa_add_directory(NAME directory [WHEN ...])`
Conditionally calls `add_subdirectory()`.

### `besa_add_source_directory(NAME directory LANGUAGE language [WHEN ...])`
Processes a language-specific root using the `include/`, `lib/<library>/`, `bin/` convention.
Multiple roots may contribute sources/headers to the shared `lib<project>` target. The generated
template places the main project's implementation below `lib/<project>/`, leaving sibling library
directories available for experiments. BESA currently collects every source below `lib/` into the
shared `lib<project>` target; separate library targets are not inferred from those directories yet.
Each direct file in `bin/` creates or contributes to an executable named after its file stem.

## Targets

### `besa_add_library(...)`

```cmake
besa_add_library(
  NAME target
  [TYPE type]
  [INSTALL TRUE|FALSE]
  [SOURCES ...]
  [HEADERS ...]
  [PUBLIC_INCLUDE_DIRECTORIES ...]
  [PRIVATE_INCLUDE_DIRECTORIES ...]
  [LINK_LIBRARIES ...]
)
```

A target named `libfoo` receives `OUTPUT_NAME foo`. BESA target policy is applied automatically.

### `besa_add_executable(...)`

```cmake
besa_add_executable(
  NAME target
  [INSTALL TRUE|FALSE]
  [SOURCES ...]
  [LINK_LIBRARIES ...]
)
```

## Tests

### `besa_test_add_directory(...)`

```cmake
besa_test_add_directory(
  NAME directory
  [PREFIX prefix]
  [LABELS ...]
  [COVERAGE_GROUP group]
  [CMDLINE ...]
  [TARGET_LIST ...]
  [MODES ...]
  [WHEN ...]
)
```

Discovers runtime `.t.<language-extension>` tests, including `.fail.t.*` and `.disabled.t.*`.

### `besa_compile_test_add_directory(...)`
Creates compile-only build tests using the same naming convention. It also accepts `MODES ...`; the
tests are created only when at least one supported mode is enabled.

### `besa_surrogate_check(TARGET target [EXPECT PASS|FAIL] [LABELS ...])`
Registers public-header self-containment checks.


## Generated public includes

### `besa_generated_include_add(NAME name [TARGET target] [OUTPUT_VARIABLE variable])`

Registers one generator-owned public include tree. BESA assigns the conventional path:

```text
<binary>/generated/<name>/include
```

When `OUTPUT_VARIABLE` is supplied, it receives that absolute path so the generator can write its
headers beneath the normal installed include namespace. Registered generated include roots are
attached to the main `lib<project>` target during project finalization and installed below
`include/`.

`TARGET` optionally names a build target that materializes the generated headers. BESA adds such
targets beneath the common `besa.generated` target and makes the main library depend on them. This
allows documentation and normal builds to materialize build-time generated headers without knowing
which generators exist.

The generator name must be one path component. The built-in version/build-metadata generator uses
`meta`, producing `<binary>/generated/meta/include/<project>/version.hpp`. Documentation and editor
discovery consume the `generated/*/include` convention rather than knowing individual generator
names.

## Documentation and QA

### `besa_add_cpdoc_docs(...)`

```cmake
besa_add_cpdoc_docs(
  NAME name
  CONFIG cpdoc.yml
  [OUTPUT_DIRECTORY directory]
  [VERSIONS_NAME name]
  [VERSIONS_OUTPUT_DIRECTORY directory]
  [NO_INSTALL]
)
```

Registers standalone API-reference targets implemented by `cpdoc`. `NAME` renders the current
checkout; `VERSIONS_NAME` defaults to `NAME.versions` and renders the Git refs selected by
`cpdoc.yml`. BESA supplies project/variant information to cpdoc, but cpdoc owns extraction, the
language-neutral API graph, HTML rendering, source pages, and version metadata.

### `besa_add_user_docs(...)`

```cmake
besa_add_user_docs(
  NAME name
  PROPERDOCS_CONFIG properdocs.yml
  CPDOC_CONFIG cpdoc.yml
  [OUTPUT_DIRECTORY directory]
  [INSTALL_DIRECTORY directory]
)
```

Registers the complete project-documentation target. ProperDocs owns the non-versioned project
website. The installed `properdocs-cpdoc` plugin invokes cpdoc and mounts its standalone versioned
API reference at the path configured in `properdocs.yml`; there is no Doxygen/Sphinx intermediate
site and no post-build assembly step.

For `NAME user.docs`, the explicit API targets are `user.docs.api` for the current checkout and
`user.docs.api.versions` for the selected version set. `user.docs` builds the deployable ProperDocs
site with the API subtree already mounted.

### `besa_add_clang_format(NAME name [LABELS ...])`
Registers a clang-format CTest check.

### `besa_add_clang_tidy(NAME name [LABELS ...] [ARGUMENTS ...])`
Registers a run-clang-tidy CTest check.
