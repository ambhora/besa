<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Run the BESA regression suite

The repository tests generate fresh template projects and exercise them rather than compiling the
checked-in template in place.

With uv:

```console
uv run --group test pytest --basetemp=build/test
```

`--basetemp` keeps generated project trees and compiler output in a predictable location. Pytest
removes that directory at the beginning of the next run.

Run only C++ integration tests:

```console
uv run --group test pytest -m cpp --basetemp=build/test
```

Run only Python template tests:

```console
uv run --group test pytest -m python --basetemp=build/test
```

The C++ test suite includes generated-project builds with GCC and Clang, package installation and a
standalone consumer, feature/selector/constraint validation, release version generation, surrogate
header compilation, and LLVM coverage reporting when the required tools are available.

The repository `spack.yaml` deliberately contains unpinned compiler, CMake, sanitizer/coverage,
Doxygen, and Python tooling specs. Activate/install that environment first when developing in the
intended toolchain environment.


## Select a generated project's test workflow

Test modes are defined by each generated project rather than by BESA. The starter C++ template
defines only `ci-commit`. A project which later defines multiple modes can select them through
`TEST_MODES`, for example:

```console
cmake -S . -B build/merge \
  -DBUILD_TESTING=ON \
  -DTEST_MODES='ci-merge;~ci-commit'
```

Tests registered with `MODES ...` are not built or registered unless one of their supported modes
is enabled.
