<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Enable instrumentation and developer tools

Instrumentation is orthogonal to structural features. Select it with `PROJECT_DEVTOOLS`:

```console
cmake -S . -B build/asan \
  -DPROJECT_DEVTOOLS='asan;surrogate' \
  -DBUILD_TESTING=ON
```

The C++ template supports:

- `format` — registers a clang-format CTest check;
- `linting` — registers a run-clang-tidy CTest check;
- `coverage` — instruments BESA-created targets and creates per-group coverage report tests/targets;
- `surrogate` — compiles each public header in an isolated generated translation unit;
- `asan` — AddressSanitizer target instrumentation;
- `lsan` — LeakSanitizer target instrumentation;
- `ubsan` — UndefinedBehaviorSanitizer target instrumentation.

`none` is the default and is mutually exclusive with every other value.

Build scripts remain instrumentation-agnostic because `besa_add_library()`, `besa_add_executable()`,
and tests created by `besa_test_add_directory()` apply the active target policy automatically.

Coverage outputs are written below:

```text
<binary-dir>/coverage/<coverage-group>/
```

Surrogate generated sources are written below:

```text
<binary-dir>/surrogate/<target>/
```


## Constrain combinations for a project

BESA defines which devtool names exist, but a project may still reject a combination that is not
valid for that project. Register a callback with `besa_register_devtool_constraint(FUNCTION ...)`
before `besa_configure_complete()`. See [Add configuration constraints](feature-constraints.md).
