# Configuration variables

BESA deliberately separates configuration families by **who defines the available names** and by
**what those names control**.

| Variable | Available names defined by | Multiple selections | Purpose |
| --- | --- | --- | --- |
| `PROJECT_FEATURES` | project | yes | Structural/project capability selection. |
| `PROJECT_DEVTOOLS` | BESA | yes | Instrumentation, diagnostics, and QA tooling. |
| `PROJECT_WARNINGS` | BESA | yes | Composable compiler warning policies. |
| `TEST_MODES` | project | yes | Selects which project-defined test workflows participate. |

## `PROJECT_FEATURES`

A semicolon-separated set of explicit feature overrides. `foo` enables a declared feature;
`~foo` disables a default feature. The same underlying feature may not occur twice, so
`foo;~foo` and `foo;foo` are configuration errors.

The project declares available/default features with `besa_features_add()` and
`besa_features_default()`.

## `PROJECT_DEVTOOLS`

A semicolon-separated instrumentation/devtool selection. BESA currently supports `format`,
`linting`, `coverage`, `surrogate`, `asan`, `lsan`, and `ubsan`. Default: `none`.

The supported set is owned by BESA and is not a project cache variable. Projects only select the
devtools they want to enable. Consequently, `besa cpp update` can make newly supported devtools
available without requiring a corresponding allow-list change in the project.

`none` explicitly disables all BESA devtools and must appear alone. Duplicate or unknown entries are
configuration errors. Projects may register constraints over the resolved devtool set with
`besa_register_devtool_constraint()`.

## `PROJECT_WARNINGS`

A semicolon-separated selection of BESA-defined warning policies. Default: `essential`.

Current policies are:

- `essential`: the normal portable warning set;
- `error`: promote compiler warnings to errors;
- `everything`: request BESA's broadest supported warning set for the active compiler;
- `none`: explicitly disable BESA warning policy and therefore must appear alone.

Warning policies are **composable**. For example:

```console
cmake -S . -B build \
  -DPROJECT_WARNINGS='essential;error'
```

This differs from the old singular `WARNING_MODE`: `error` no longer implicitly chooses the
`essential` policy. The project selects every policy it wants to combine. The supported policy names
are owned by BESA rather than declared by individual projects.

## `TEST_MODES`

A semicolon-separated set of explicit overrides to the project's default test modes. Test modes use
the same override model as features: `ci-merge` enables a declared mode and `~ci-commit` disables a
default mode. The same underlying mode may not appear more than once.

Test-mode names are **project-defined and semantically opaque to BESA**. The starter C++ template
currently declares only `ci-commit`:

```cmake
besa_test_modes_add(
  MODES
    ci-commit
)

besa_test_modes_default(
  MODES
    ci-commit
)
```

A project can later add `ci-merge`, `nightly`, `system`, or any other workflow without changing
BESA. Tests declare the modes they support through their `MODES` argument. A test with multiple
supported modes participates when **any one** of them is enabled. Omitting `MODES` means that the
test supports every test mode.

Projects may register constraints over the resolved test-mode set with
`besa_register_test_mode_constraint()`.

## `BUILD_TESTING`

Controls construction of the project test graph. The C++ template defaults it to `OFF` before
including CTest.

## `RELEASE_TYPE`

One of `dev`, `release`, `alpha`, `beta`, or `rc`. See [Release process](release-process.md) for the
release-management workflow and [Versioning](versioning.md) for the generated version strings.

## `RELEASE_REVISION`

The prerelease revision for alpha, beta, and release-candidate versions.

For `dev`, the resolved version is `dev.<branch>.<hash>` (with `nogit` fallbacks); release and
prerelease types use the declared project version.

BESA writes the resolved semantic version to `PROJECT_SEMVER`, generates
`<binary>/generated/include/<project>/version.hpp`, and writes the same resolved string into the
installed package configuration.

## Configure-time summary

`besa_configure_complete()` prints the **resolved** configuration after defaults, explicit overrides,
constraints, toolchain-language activation, and release-version resolution. This makes it easy to
verify what BESA actually detected and selected from a configure invocation.

A typical summary is:

```text
-- BESA configuration:
--   Features      : build-source, toolchain-cpp, user-docs
--   Devtools      : coverage
--   Warning policy: essential
--   Test modes    : ci-commit
--   Languages     : CXX
--   Build testing : ON
--   Release type  : dev
--   Release rev.  : 1
--   Version       : dev.main.abc1234
```

The summary intentionally reports resolved sets rather than the raw cache-variable text. For
example, default features remain visible even when `PROJECT_FEATURES` contains only an additional
`user-docs` override.
