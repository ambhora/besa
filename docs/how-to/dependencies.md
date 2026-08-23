<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Add dependencies

Declare a CMake-resolved normal dependency with:

```cmake
besa_dependency_add(
  NAME fmt
  KIND NORMAL
  PROVIDER CMAKE
  VISIBILITY PRIVATE
)
```

Declare a development-only dependency with:

```cmake
besa_dependency_add(
  NAME Catch2
  VERSION 3
  KIND DEV
  PROVIDER CMAKE
)
```

Conditional dependencies use the same selector grammar as directories:

```cmake
besa_dependency_add(
  NAME Doxygen
  KIND DEV
  PROVIDER CMAKE
  WHEN ALL_OF user-docs
)
```

For pkg-config metadata use `PROVIDER PKGCONFIG`.

`NORMAL` dependencies are recorded in the generated `<project>Config.cmake`. `BUILD` and `DEV`
dependencies are intentionally absent from consumer package metadata.
