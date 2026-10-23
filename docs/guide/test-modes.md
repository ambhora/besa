# Test modes

A **test mode** is a project-defined name for a testing workflow: the quick
set run on every commit, the full set run before merging, a nightly set, a
site-specific validation run. Test directories declare which modes support
them; the user selects a mode; BESA registers the matching directories.

BESA attaches **no meaning** to mode names. `commit`, `ci-merge`, `nightly`
and `tier1` are all just labels the project chooses.

## Declaring modes

In the options file, before `besa_finalize_options()`:

```cmake
set(TEST_MODE "ci-commit" CACHE STRING "Selected test mode")
set_property(CACHE TEST_MODE PROPERTY STRINGS ci-commit ci-merge)

besa_test_modes_add(MODES ci-commit ci-merge)
besa_test_modes_default(MODES ci-commit)

besa_register_options(GROUP build VARIABLES TEST_MODE)
```

`besa_test_modes_add()` declares the available names. `besa_test_modes_default()`
chooses which of them are enabled when the user says nothing. Declared names
may not start with `~`.

## Selecting modes

Two cache variables control the selection; both are optional.

`TEST_MODE`
:   Selects **exactly one** declared mode, replacing the defaults. `none`
    selects no mode. An unknown name fails:
    `unknown TEST_MODE 'nightly'; declared modes: ci-commit;ci-merge`.

`TEST_MODES`
:   A list of **overrides** applied after `TEST_MODE`/defaults: `name` adds a
    mode, `~name` removes one. Each mode may appear at most once.

The resolution is: start from the defaults; if `TEST_MODE` is set, replace
them with that one mode (or nothing for `none`); then apply `TEST_MODES`.

```bash
cmake -B build                                 # ci-commit (the default)
cmake -B build -DTEST_MODE=ci-merge            # ci-merge only
cmake -B build -DTEST_MODES="ci-merge"         # ci-commit + ci-merge
cmake -B build -DTEST_MODES="~ci-commit"       # nothing
cmake -B build -DTEST_MODE=none                # nothing
```

Projects that only ever want one mode at a time expose `TEST_MODE` and leave
`TEST_MODES` for power users; it exists as a cache variable either way.

## Using modes

Test directories list the modes that support them:

```cmake
besa_test_add_directory(NAME commit PREFIX commit MODES ci-commit ci-merge)
besa_test_add_directory(NAME merge  PREFIX merge  MODES ci-merge)
```

With the default `ci-commit`, only `commit/` is registered. With
`-DTEST_MODE=ci-merge`, both are. A directory without `MODES` is registered
in every mode, including `none`.

Elsewhere in the project, query the resolved set:

```cmake
besa_test_modes_check(OUTPUT_VARIABLE FULL_RUN MODES ci-merge)
if(FULL_RUN)
  set_tests_properties(commit.stress.t PROPERTIES TIMEOUT 1800)
endif()
```

or use the published booleans `PROJECT_TEST_MODE_CI_COMMIT`,
`PROJECT_TEST_MODE_CI_MERGE`, … and the list `BESA_ENABLED_TEST_MODES`.

## Validating mode sets

If some combinations of modes make no sense, register a constraint:

```cmake
function(myproject_check_modes)
  besa_test_mode_constraint_arguments_parse(PREFIX ARG ARGUMENTS ${ARGN})
  list(LENGTH ARG_MODES count)
  if(count GREATER 1)
    set(${ARG_OUTPUT_VARIABLE} FALSE PARENT_SCOPE)
    set(${ARG_ERROR_VARIABLE} "select a single test mode" PARENT_SCOPE)
    return()
  endif()
  set(${ARG_OUTPUT_VARIABLE} TRUE PARENT_SCOPE)
endfunction()
besa_register_test_mode_constraint(FUNCTION myproject_check_modes)
```

Constraints run during `besa_finalize_options()` with the fully resolved
mode list and fail configuration with the supplied message.

## Modes versus features versus devtools

The three selection axes are deliberately separate:

| Axis | Answers | Changes the built code? | Selected by |
| --- | --- | --- | --- |
| Features | What can the product do? | Yes | `PROJECT_FEATURE` |
| Devtools | How is this build instrumented? | Yes (flags) | `BUILD_DEVTOOLS` |
| Test modes | Which tests run? | No | `TEST_MODE` / `TEST_MODES` |

A test that needs the GPU uses `CONDITION gpu`. A test that only makes sense
under AddressSanitizer uses `DEVTOOLS asan`. A test that is simply slow uses
`MODES ci-merge`. Keeping them apart means a CI matrix can vary one without
re-deriving the others.
