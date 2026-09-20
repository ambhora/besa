<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Add dependencies

Declare dependencies in `besa.toml`. For example, the TOML equivalent of a development-only CMake
provider dependency is:

```toml
[[dependencies]]
name = "Catch2"
version = "3"
kind = "dev"
provider = "cmake"
```

A conditional documentation dependency is:

```toml
[[dependencies]]
name = "Doxygen"
kind = "dev"
provider = "cmake"
when = { all = ["user-docs"] }
```

Supported dependency kinds are `normal`, `build`, and `dev`; providers are `cmake` and `pkgconfig`.
`visibility` and `components` may also be supplied when required.

`normal` dependencies are recorded in the generated `<project>Config.cmake`. `build` and `dev`
dependencies are intentionally absent from consumer package metadata.

This model does not integrate with Spack. A Spack development environment declares and resolves its
own dependency set independently, including any package-name differences. `provider = "cmake"`
describes how the CMake backend resolves this project dependency; it is not a package-manager
identity shared with Spack.
