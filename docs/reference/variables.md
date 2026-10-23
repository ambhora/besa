# Cache variables

## Set by the user or the project

BESA reads these during `besa_finalize_options()`. If the project has not
declared one, BESA creates it with the default shown (except where noted).

| Variable | Default | Type | Description |
| --- | --- | --- | --- |
| *feature variable* (`PROJECT_FEATURE` by convention) | — | list | Enabled features; connected with `besa_set_feature_variable()`. `none` and empty entries are ignored. Falls back to `PROJECT_FEATURES`, then to the project space default |
| `BUILD_DEVTOOLS` | `none` | list | Any of `format linting coverage surrogate asan lsan ubsan`, or `none` alone. Legacy: `PROJECT_DEVTOOLS` |
| `BUILD_WARNINGS` | `minimal` | list | At most one of `minimal extra everything`, optionally `werror`; or `none` alone. Legacy: `PROJECT_WARNINGS` (`essential`→`extra`, `error`→`werror`) |
| `BUILD_TESTING` | *(CTest's)* | bool | Enables devtool-driven tests; projects usually gate their own test directories on it |
| `TEST_MODE` | *(not created)* | string | Exactly one declared test mode, or `none`. Replaces the defaults when defined |
| `TEST_MODES` | *(empty)* | list | Overrides: `mode` adds, `~mode` removes |
| `RELEASE_TYPE` | `dev` | string | `dev`, `alpha`, `beta`, `rc`, `release` |
| `RELEASE_REVISION` | `1` | string | Pre-release revision |
| `PKGBUILDER_ID` | `vanilla` | string | Package builder identifier |
| `PKGBUILDER_REVISION` | `1` | string | Package builder revision |
| `BESA_WORKSPACE` | `<build>/besa` | path | Root of BESA-owned build-tree files |
| `BESA_COVERAGE_OUTDIR` | `<build>/coverage` | path | Coverage report root (coverage devtool only) |
| `BESA_CPDOCS_FEATURE_SETS_OUTPUT` | — | path | If set, write every valid feature set to this JSON file at finalization |
| `BESA_CPDOCS_FEATURE_SET` | — | path | If set, read a `cpdocs-feature-set` JSON file and force the feature variable to its features |
| `BESA_CPDOCS_MANIFEST_OUTPUT` | — | path | If set, write the cpdocs manifest to this JSON file and create the `besa.cpdocs` target |
| `BUILD_SHARED_LIBS` | — | bool | Standard CMake; honoured by libraries without `TYPE` |
| `CMAKE_EXPORT_COMPILE_COMMANDS` | forced `ON` | bool | Set by `besa_finalize_options()` |

Variables for installing BESA itself (not consumer projects):
`BESA_INSTALL_DATADIR` (`share`) and `BESA_INSTALL_CMAKEDIR`
(`share/besa/cmake`).

## Published by BESA

Internal cache variables written by `besa_finalize_options()` and the
finalizers. Read them; do not set them. `<NAME>` is the upper-cased name
with every character outside `A-Z0-9_` replaced by `_`.

| Variable | Content |
| --- | --- |
| `BESA_ENABLED_FEATURES` | Sorted list of enabled features |
| `PROJECT_FEATURE_<NAME>` | `TRUE`/`FALSE` per declared feature |
| `BESA_ENABLED_DEVTOOLS` | List of enabled devtools |
| `BUILD_DEVTOOLS_<NAME>` | `TRUE`/`FALSE` per supported devtool (`BUILD_DEVTOOLS_ASAN`, …) |
| `BESA_ENABLED_WARNINGS` | List of enabled warning policies |
| `BUILD_WARNINGS_<NAME>` | `TRUE`/`FALSE` per policy (`BUILD_WARNINGS_WERROR`, …) |
| `BESA_ENABLED_TEST_MODES` | List of enabled test modes |
| `PROJECT_TEST_MODE_<NAME>` | `TRUE`/`FALSE` per declared mode |
| `PROJECT_SEMVER` | Resolved semantic version string |
| `BESA_MANIFEST` | Path of `manifest.json` (after finalization) |
| `BESA_BUILD_DIRECTORY` | `PROJECT_BINARY_DIR` |
| `BESA_CODEGEN_DIRECTORY` | `<workspace>/codegen` |
| `BESA_DOCS_DIRECTORY` | `<workspace>/docs` |
| `BESA_CONFIGURE_CACHE_DIRECTORY` | `<workspace>/configure_cache` |
| `BESA_COVERAGE_COMPILER` | `clang` or `gcc` (coverage devtool only) |

Tool paths found by devtools are cached as `BESA_CLANG_FORMAT`,
`BESA_CLANG_TIDY`, `BESA_RUN_CLANG_TIDY`, `BESA_LLVM_PROFDATA`,
`BESA_LLVM_COV` and `BESA_GCOVR`; override them on the command line to pin
a specific binary.

## Global properties

BESA keeps its registries in global properties prefixed `BESA_`. They are
implementation details and may change between releases; use the query
commands and the published variables above instead.
