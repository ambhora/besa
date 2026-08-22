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

### `besa_add_doxygen(NAME name DOXYFILE file [OUTPUT_DIRECTORY directory])`
Creates a raw Doxygen target. This lower-level helper remains available for projects which want
Doxygen output directly.

### `besa_add_sphinx_breathe_docs(...)`

```cmake
besa_add_sphinx_breathe_docs(
  NAME name
  SOURCE_DIRECTORY directory
  [OUTPUT_DIRECTORY directory]
  [MULTIVERSION_NAME name]
  [MULTIVERSION_OUTPUT_DIRECTORY directory]
  [MULTIVERSION_DEFAULT_VERSION ref]
  [DOXYGEN_OUTPUT_DIRECTORY directory]
  [SITE_ROOT_DEPTH number]
  [NO_INSTALL]
)
```

Registers the API-rendering layer only. `NAME` builds the current checkout with Sphinx;
`MULTIVERSION_NAME` builds the Git refs selected by `BESA_API_VERSIONS` (or the generated
`properdocs.yml` default) with sphinx-multiversion. Doxygen produces XML for each checkout and
Breathe exposes that XML to Sphinx.

The multiversion root contains one Sphinx tree per selected ref plus `versions.json`. It deliberately
does not create a root `index.html`: when used by `besa_add_user_docs()`, ProperDocs owns the API
landing page and the whole documentation-site root.

`SITE_ROOT_DEPTH` is passed to Sphinx so the generated API sidebar can construct relative links back
to the canonical ProperDocs site. `NO_INSTALL` is used by the high-level assembler so only the final
combined site is installed.

### `besa_add_user_docs(...)`

```cmake
besa_add_user_docs(
  NAME name
  PROPERDOCS_CONFIG properdocs.yml
  API_SOURCE_DIRECTORY api-docs
  [API_PATH reference/api]
  [OUTPUT_DIRECTORY directory]
  [MULTIVERSION_DEFAULT_VERSION main]
  [DOXYGEN_OUTPUT_DIRECTORY directory]
  [INSTALL_DIRECTORY directory]
)
```

Registers the complete documentation publication pipeline. ProperDocs is built as the canonical
site; the Doxygen/Breathe/Sphinx multiversion API tree is assembled below `API_PATH`. The final
`NAME` target writes one deployable tree (default `<binary>/doc/site`) and installs that assembled
site below `CMAKE_INSTALL_DOCDIR` when it has been built.

For `NAME user.docs`, the derived targets are:

- `user.docs.properdocs` — ProperDocs only;
- `user.docs.api` — current-checkout API only;
- `user.docs.multiversion` — raw multiversion API tree;
- `user.docs` — final ProperDocs + versioned API publication site.

The API mount path is also used to derive the relative navigation depth supplied to Sphinx, so links
from API pages back to ProperDocs do not depend on a deployment hostname or GitHub Pages repository
prefix.

### `besa_add_clang_format(NAME name [LABELS ...])`
Registers a clang-format CTest check.

### `besa_add_clang_tidy(NAME name [LABELS ...] [ARGUMENTS ...])`
Registers a run-clang-tidy CTest check.
