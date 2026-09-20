<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Instrumentation and developer-tool reference

Instrumentation is selected through `PROJECT_DEVTOOLS` and resolved by
`besa_configure_complete()`. It is orthogonal to structural features: changing instrumentation must
not require changing the project's source/dependency topology.

The generated C++ template currently allows:

| Value | Effect |
| --- | --- |
| `format` | Registers a clang-format CTest QA check. |
| `linting` | Registers a clang-tidy/run-clang-tidy CTest QA check. |
| `coverage` | Instruments BESA-created targets and registers coverage groups/reports. |
| `surrogate` | Compiles every public header in an isolated generated translation unit. |
| `asan` | Applies AddressSanitizer compile/link policy. |
| `lsan` | Applies LeakSanitizer compile/link policy. |
| `ubsan` | Applies UndefinedBehaviorSanitizer compile/link policy. |
| `none` | Disables all instrumentation/devtools and must appear alone. |

Multiple non-`none` values are a semicolon-separated set:

```console
cmake -S . -B build/diagnostic \
  -DPROJECT_DEVTOOLS='asan;surrogate'
```

Duplicate values and unknown values are configuration errors.

## Automatic target policy

Targets created through `besa_add_library()`, `besa_add_executable()`, conventional source
directories, and runtime test discovery automatically receive active sanitizer/coverage policy.
Project build scripts do not contain sanitizer or coverage compiler flags.

BESA uses build-interface policy targets so BESA-specific instrumentation targets do not leak into
installed exported targets.

## Surrogate headers

When `surrogate` and `BUILD_TESTING` are enabled, every installed/project library created by BESA is
registered for public-header self-containment checking. The generated files are written under:

```text
<binary-dir>/surrogate/<target>/
```

Each recognized `.h`, `.hpp`, `.hh`, `.hxx`, `.cuh`, or `.cuhpp` header becomes a minimal source file
containing only the corresponding `#include`. CTest builds an excluded-from-all surrogate target.

## Coverage

`besa_test_add_directory(COVERAGE_GROUP ...)` associates runtime tests with coverage groups.
With Clang, BESA uses LLVM profile instrumentation and `llvm-profdata`/`llvm-cov`; with GCC it uses
compiler coverage instrumentation plus `gcovr` for reporting.

Reports live under:

```text
<binary-dir>/coverage/<group>/
```

The aggregate CTest name is `instrumentation.coverage.t`, with per-group tests named
`instrumentation.coverage.<group>.t`.
