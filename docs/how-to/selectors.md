<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Use feature conditions

Conditional dependencies, sources, and directories in `besa.toml` use structural feature
conditions. The three operators may be nested.

## `all`

```toml
when = { all = ["toolchain-cuda", "mpi"] }
```

Every operand must match.

## `any`

```toml
when = { any = ["toolchain-cuda", "toolchain-hip"] }
```

At least one operand must match.

## `not`

```toml
when = { all = ["toolchain-cpp", { not = "toolchain-cuda" }] }
```

`not` may contain one feature name or another nested condition.

For feature logic that is not naturally expressible with these operators, register a portable
Python feature constraint in `besa.toml`; see [Add configuration constraints](feature-constraints.md).

The CMake module still exposes its lower-level selector API for backend-specific CMake code, but
normal project topology should be expressed in `besa.toml` so another backend can consume the same
project declaration.
