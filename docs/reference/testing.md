# Test conventions

## Test modes

Test modes are project-defined workflow names. BESA does not attach special meaning to names such as
`ci-commit`, `ci-merge`, or `nightly`.

Declare the available/default modes before `besa_configure_complete()`:

```cmake
besa_test_modes_add(
  MODES
    ci-commit
    ci-merge
)

besa_test_modes_default(
  MODES
    ci-commit
)
```

`TEST_MODES` applies explicit overrides using the same rules as `PROJECT_FEATURES`:

```console
cmake -S . -B build/merge \
  -DTEST_MODES='ci-merge;~ci-commit'
```

Duplicate underlying names such as `ci-commit;~ci-commit` are errors.

## Mode-aware test registration

`besa_test_add_directory()` and `besa_compile_test_add_directory()` accept `MODES`. The argument
lists the test modes supported by those tests and uses any-overlap semantics:

```cmake
besa_test_add_directory(
  NAME cpp/vorlage
  PREFIX unit
  MODES
    ci-commit
    ci-merge
)
```

The discovered targets/tests are created only if at least one listed mode is enabled. Omitting
`MODES` means the tests support all modes.

For manually constructed tests or an entire manually managed test subtree, use:

```cmake
besa_test_modes_check(
  OUTPUT_VARIABLE _enabled
  MODES ci-commit
)

if(_enabled)
  add_subdirectory(smoke)
endif()
```

This ensures mode-disabled tests are not merely skipped at runtime: their build targets are not
created either.

## Test-mode constraints

Projects may register a named callback with `besa_register_test_mode_constraint(FUNCTION ...)`.
Callbacks receive the fully resolved enabled mode set and may reject invalid combinations before the
configuration phase is frozen. See [Add configuration constraints](../how-to/feature-constraints.md).

## Test library

The C++ template creates `libtest<project>` as a test-only interface library. It owns the dependency
graph shared by tests without adding those dependencies to the production library or installed
package.

## Runtime test names

`besa_test_add_directory()` recognizes source files such as:

```text
true.t.cpp
false.fail.t.cpp
slow.disabled.t.cpp
```

`.fail.t` tests receive CTest `WILL_FAIL`; `.disabled.t` tests receive `DISABLED`.

## Compile tests

`besa_compile_test_add_directory()` creates targets excluded from the normal build and registers
CTest entries which explicitly build those targets. `.fail.t` means the target is expected not to
compile.

## Smoke tests

The template includes the established C++ smoke checks for:

- thread creation/execution;
- AddressSanitizer activation;
- LeakSanitizer activation;
- UndefinedBehaviorSanitizer activation.

Sanitizer smoke tests are added only when the corresponding devtool is enabled. The starter template
gates its manually registered smoke subtree with the `ci-commit` test mode.

## Coverage groups

Pass `COVERAGE_GROUP` to runtime test discovery. When `coverage` is enabled, BESA registers the test
with that group and creates coverage report tests/targets during finalization.
