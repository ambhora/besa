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
<binary-dir>/generated/include/<project>/version.hpp
```

and attaches that generated header to the main `lib<project>` file set when the conventional source
layout creates the library.

During installation, BESA writes the resolved version string into `<project>Config.cmake` and uses
the base `PROJECT_VERSION` to generate `<project>ConfigVersion.cmake` compatibility metadata.
