<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Release process

BESA separates the version declared by the project from the release state of a particular build.
The project continues to declare its base version with the normal CMake `project()` command:

```cmake
project(vorlage VERSION 0.1.0 LANGUAGES NONE)
```

Release management is then controlled by two cache variables:

```cmake
set(RELEASE_TYPE "dev" CACHE STRING "Type of Release")
set(RELEASE_REVISION "1" CACHE STRING "Revision of Release")
```

These variables are intentionally small, but they form the boundary between ordinary development
builds and builds intended to represent a release or prerelease. For the exact version strings
produced from these values, see [Versioning](versioning.md).

## `RELEASE_TYPE`

`RELEASE_TYPE` selects the release state represented by the build. BESA accepts:

| Value | Purpose |
| --- | --- |
| `dev` | Ordinary development build. BESA derives the version from Git rather than treating the build as a release. |
| `alpha` | Alpha prerelease of `PROJECT_VERSION`. |
| `beta` | Beta prerelease of `PROJECT_VERSION`. |
| `rc` | Release candidate of `PROJECT_VERSION`. |
| `release` | Final release corresponding exactly to `PROJECT_VERSION`. |

Generated projects default to:

```cmake
set(RELEASE_TYPE "dev" CACHE STRING "Type of Release")
```

This keeps an ordinary developer configure from accidentally describing itself as a release.

## `RELEASE_REVISION`

`RELEASE_REVISION` distinguishes successive prereleases of the same base project version. It is used
for `alpha`, `beta`, and `rc` builds.

For example, with:

```cmake
project(vorlage VERSION 1.4.0 LANGUAGES NONE)
```

and:

```text
RELEASE_TYPE=rc
RELEASE_REVISION=2
```

BESA resolves the project version as:

```text
1.4.0-rc.2
```

`RELEASE_REVISION` does not alter a final `release` version, and development versions use Git
metadata instead.

## Development builds

Normal development should leave the default release type unchanged:

```bash
cmake -S . -B build
```

or explicitly:

```bash
cmake -S . -B build -DRELEASE_TYPE=dev
```

During `besa_configure_complete()`, BESA resolves a Git-derived development version and stores the
result in `PROJECT_SEMVER`.

A development build therefore does not require the project author to change `PROJECT_VERSION` for
every commit.

## Preparing a prerelease

First set the intended base release in `project()`:

```cmake
project(vorlage VERSION 1.4.0 LANGUAGES NONE)
```

Then configure the desired prerelease explicitly. For the first release candidate:

```bash
cmake \
  -S . \
  -B build/rc1 \
  -DRELEASE_TYPE=rc \
  -DRELEASE_REVISION=1
```

A subsequent release candidate changes only the revision:

```bash
cmake \
  -S . \
  -B build/rc2 \
  -DRELEASE_TYPE=rc \
  -DRELEASE_REVISION=2
```

The same process applies to alpha and beta releases:

```bash
cmake -S . -B build/alpha1 -DRELEASE_TYPE=alpha -DRELEASE_REVISION=1
cmake -S . -B build/beta1  -DRELEASE_TYPE=beta  -DRELEASE_REVISION=1
```

The release type and revision should be supplied explicitly by the release workflow so that a
release build does not depend on a developer's local cache state.

## Preparing the final release

For the final release, keep the same `PROJECT_VERSION` and configure with:

```bash
cmake \
  -S . \
  -B build/release \
  -DRELEASE_TYPE=release
```

The resolved version is then exactly `PROJECT_VERSION`; `RELEASE_REVISION` is not part of the final
version string.

This allows alpha, beta, release-candidate, and final builds to share the same base project version
while making the release state explicit at configure time.

## What BESA derives

`besa_configure_complete()` processes the release variables and provides:

```cmake
PROJECT_SEMVER
```

as the resolved version for the current build. BESA also uses the resolved release information when
it generates the project's version header and installed package metadata.

The release process therefore has a simple division of responsibility:

- `project(... VERSION ...)` declares the base software version;
- `RELEASE_TYPE` declares whether the build is development, prerelease, or final;
- `RELEASE_REVISION` identifies a particular prerelease iteration;
- BESA derives the concrete version used by the build and generated metadata.

## Release automation

BESA does not require a particular CI/CD release mechanism. A release job only needs to provide the
appropriate CMake cache values when it configures the project. This keeps release policy outside the
normal project build description while giving the build an explicit and reproducible release state.
