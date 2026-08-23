<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Use feature selectors

Functions which conditionally add project structure accept a named `WHEN` argument. Four selector
forms are supported.

## ALL_OF

```cmake
besa_add_directory(
  NAME src/cuda_support
  WHEN ALL_OF toolchain-cuda mpi
)
```

Every atom must match. Prefix an atom with `~` to require that feature to be disabled:

```cmake
WHEN ALL_OF toolchain-cpp ~toolchain-cuda
```

## ANY_OF

```cmake
besa_add_directory(
  NAME accelerator
  WHEN ANY_OF toolchain-cuda toolchain-hip
)
```

At least one atom must match.

## REGEX

`REGEX` succeeds when at least one resolved enabled feature matches the regular expression:

```cmake
besa_add_directory(NAME project WHEN REGEX "^project-")
besa_add_directory(NAME showcases WHEN REGEX "^showcase-")
```

The value is a regular expression, not a glob.

## FUNCTION

A custom selector is useful when a condition cannot be expressed by lists or a regular expression.
The callback uses named arguments and can use `besa_selector_arguments_parse()` to avoid duplicating
argument parsing boilerplate.
