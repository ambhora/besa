# Build targets and tests

## Targets created from project declarations

| Declaration | Target(s) | Alias |
| --- | --- | --- |
| `besa_add_library(NAME libfoo)` | `libfoo` (output `foo`) | `<project>::libfoo` |
| `besa_add_executable(NAME tool)` | `tool` | — |
| `besa_add_subdirectory(DIRECTORY bin TYPE bin)` | one per file: `bin/x.cpp` → `x` | — |
| `besa_test_add_directory(NAME t PREFIX p)` | one per test: `t/a/b.t.cpp` → `p.a.b.t` | — |
| `besa_compile_test_add_directory(...)` | same naming, `EXCLUDE_FROM_ALL` | — |
| `besa_surrogate_check(TARGET libfoo)` | `surrogate.libfoo.t` (`EXCLUDE_FROM_ALL`) | — |
| generated unit with a generator target | the callback's target, plus a `CODEGEN` stamp | — |

## Targets created by BESA

| Target | Exists when | Purpose |
| --- | --- | --- |
| `codegen` | CMake's reserved target; populated when any generated unit returns a generator target | Runs every generator without compiling |
| `besa.cpdocs` | `BESA_CPDOCS_MANIFEST_OUTPUT` is set | Depends on all generator targets; cpdocs builds it before extraction |
| `besa.coverage` | `coverage` devtool, `BUILD_TESTING`, at least one `COVERAGE_GROUP` | Builds every group report |
| `besa.coverage.<group>` | as above, per group | Builds one group's report |
| `<NAME>`, `<NAME>.versions` | `besa_add_cpdocs_docs(NAME <NAME>)` | cpdocs current / versioned API |
| `<NAME>`, `<NAME>.api`, `<NAME>.api.versions` | `besa_add_user_docs(NAME <NAME>)` | ProperDocs site and its cpdocs inputs |

## Interface targets (usage requirements)

These are always defined by `find_package(besa)` and may be linked to
hand-made targets to opt them into BESA's policies. They are `PRIVATE`
build-interface-only in BESA's own use and never exported.

| Target | Carries |
| --- | --- |
| `besa::warning.minimal` | `-Wall` |
| `besa::warning.extra` | `-Wextra -Wpedantic -Wdeprecated` (+ minimal) |
| `besa::warning.everything` | Clang `-Weverything` with a few `-Wno-` (+ extra) |
| `besa::warning.werror` | `-Werror` |

Defined only when the corresponding devtool is enabled:

| Target | Carries |
| --- | --- |
| `besa::asan` | AddressSanitizer compile/link options |
| `besa::lsan` | LeakSanitizer |
| `besa::ubsan` | UndefinedBehaviorSanitizer |
| `besa::coverage` | Clang source-based or GCC `--coverage` instrumentation |

## CTest tests created by BESA

| Test | Created when | Labels | What it does |
| --- | --- | --- | --- |
| `<prefix>.<path>.t` | test discovery | project's `LABELS` | Runs the test executable |
| `<prefix>.<path>.fail.t` | test discovery | project's `LABELS` | Same, `WILL_FAIL` |
| `<prefix>.<path>.disabled[.fail].t` | test discovery | project's `LABELS` | Same, `DISABLED` |
| compile tests | `besa_compile_test_add_directory()` | project's `LABELS` | `cmake --build --target <test>` |
| `surrogate.<library>.t` | `surrogate` devtool (automatic) or `besa_surrogate_check()` | `instrumentation surrogate` | Builds the header-check library |
| `instrumentation.format.t` | `format` devtool + `BUILD_TESTING` | `instrumentation format` | `clang-format --dry-run -Werror` |
| `instrumentation.linting.t` | `linting` devtool + `BUILD_TESTING` | `instrumentation linting` | `run-clang-tidy` |
| `instrumentation.coverage.<group>.t` | `coverage` devtool, per group | `instrumentation coverage` | Builds `besa.coverage.<group>`; `DEPENDS` on the group's tests |
| `instrumentation.coverage.t` | `coverage` devtool | `instrumentation coverage` | Builds `besa.coverage`; `DEPENDS` on all group reports |

Useful selections:

```bash
ctest -LE instrumentation        # only the project's own tests
ctest -L coverage                # tests + reports, in dependency order
ctest -R '\.fail\.t$'            # every expected-failure test
```

## Files written to the build tree

| Path | Written by |
| --- | --- |
| `besa/manifest.json` | manifest finalizer |
| `besa/codegen/meta/include/<project>/version.hpp` | `besa_finalize_options()` |
| `besa/codegen/<unit>/{include,lib,mod}` | generated unit callbacks |
| `besa/codegen/<unit>.stamp` | `CODEGEN` custom commands |
| `besa/subdirectories/<unit>/` | scratch for generated unit callbacks |
| `besa/package/<project>Config.cmake`, `…ConfigVersion.cmake`, `write-install-manifest.cmake` | package finalizer |
| `besa/docs/…` | documentation targets |
| `surrogate/<library>/…` | surrogate checks (generated `#include` sources) |
| `coverage/<group>/…` | coverage reports |
| `compile_commands.json` | CMake, because BESA forces `CMAKE_EXPORT_COMPILE_COMMANDS` |
