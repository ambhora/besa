<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# besa-dev

Developer tooling for BESA, independent of the BESA CMake package. It owns the
compiler matrix tested in CI, described in `etc/compilers.json`.

```sh
uv run --project dev besa-dev list               # configured compilers
uv run --project dev besa-dev matrix             # GitHub Actions matrix
uv run --project dev besa-dev run gcc-16         # test locally in a container
uv run --project dev besa-dev discover           # report upstream releases
uv run --project dev besa-dev discover --write   # and update compilers.json
```

## The compiler configuration

`families` says, for each compiler family, how releases are discovered, which
container image provides a version, which commands prepare the image, and the
`CC`, `CXX`, and extra `PATH` entries to use. Any string may contain
`{version}`, replaced by the major version. `compilers` lists the versions
under test; `experimental: true` lets a job fail without failing the workflow.

Discovery adds every upstream major version at or above the family `minimum`.
It never drops a listed version except one below the `minimum`, so raising a
`minimum` is how old compilers are retired. Supporting a new family means
adding an entry to `families`; supporting a new version needs nothing.

## Running locally

`besa-dev run <id>` runs exactly the container command used in CI. The build
tree is `build/ci-<id>` and is written by root inside the container.
