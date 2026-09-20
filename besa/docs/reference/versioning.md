<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Release and versioning reference

The normal CMake `project(... VERSION ...)` value is the release base version. BESA adds release
state without making project build files compute Git metadata themselves. The operational use of
`RELEASE_TYPE` and `RELEASE_REVISION` is described in the [Release process](release-process.md).

## `RELEASE_TYPE`

`RELEASE_TYPE` is selected as part of the [release process](release-process.md). Accepted values:

- `dev` — use a Git-derived development version instead of the release base version;
- `release` — use exactly `PROJECT_VERSION`;
- `alpha` — `<PROJECT_VERSION>-alpha.<RELEASE_REVISION>`;
- `beta` — `<PROJECT_VERSION>-beta.<RELEASE_REVISION>`;
- `rc` — `<PROJECT_VERSION>-rc.<RELEASE_REVISION>`.

For `dev`, BESA resolves the current branch and short commit and produces
`dev.<branch>.<hash>`. Missing/unavailable Git information uses stable `nogit` fallbacks.

## Generated values

After `besa_configure_complete()`:

```cmake
PROJECT_SEMVER
```

contains the resolved string. BESA also writes:

```text
<binary-dir>/generated/meta/include/<project>/version.hpp
```

The `meta` generator registers that include root with BESA; project finalization attaches registered
generated include roots to the main `lib<project>` target and installation. The header exposes compile-time metadata in `<project>::meta`:

```cpp
auto constexpr version = project::meta::version();
auto constexpr release = project::meta::release();
auto constexpr package = project::meta::package();
auto constexpr build = project::meta::build();

static_assert(version.major == 1);
static_assert(project::meta::to_string(version) == "1.2.3");
static_assert(project::meta::to_string(release.type) == "rc");
```

`version()` returns a `semantic_version` with `major`, `minor`, `patch`, and `tweak` components derived
from CMake's `PROJECT_VERSION_*` values. Missing components are zero.

`release()` returns a `release_info` containing the resolved release kind and revision. The enum
values are `development`, `release`, `alpha`, `beta`, and `release_candidate`.

`package()` returns a `package_info` containing the downstream package-builder identity and package
revision. These values come from `PKGBUILDER_ID` and `PKGBUILDER_REVISION`; they do not alter the
upstream semantic version or release information. The defaults are `vanilla` and `1`. A downstream
builder can, for example, configure with `-DPKGBUILDER_ID=spack -DPKGBUILDER_REVISION=2`.

`build()` returns `build_info` with only CMake-derived build metadata:

- C++ compiler ID;
- C++ compiler version;
- target system name;
- target processor;
- build type (or `multi-config` / `none` when appropriate).

String conversion is explicit. `project::meta::to_string(...)` converts the structured metadata to
canonical string forms such as the base `PROJECT_VERSION`, `rc.2`, or a compact build-description
string.

During installation, BESA writes the resolved version string into `<project>Config.cmake` and uses
the base `PROJECT_VERSION` to generate `<project>ConfigVersion.cmake` compatibility metadata.
