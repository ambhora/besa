<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Add configuration constraints

BESA lets a project reject otherwise valid combinations in three independently resolved
configuration families:

- project features;
- BESA devtools;
- project test modes.

Constraints run inside `besa_configure_complete()` after defaults/overrides have been resolved, but
before toolchain languages or compiler-dependent instrumentation are activated. Each callback uses
named arguments and returns a boolean plus an optional error message.

## Feature constraints

Define a callback:

```cmake
function(no_cuda_and_hip)
  besa_feature_constraint_arguments_parse(
    PREFIX ARG
    ARGUMENTS ${ARGN}
  )

  if("toolchain-cuda" IN_LIST ARG_FEATURES
     AND "toolchain-hip" IN_LIST ARG_FEATURES)
    set("${ARG_OUTPUT_VARIABLE}" FALSE PARENT_SCOPE)
    set(
      "${ARG_ERROR_VARIABLE}"
      "CUDA and HIP cannot be enabled together in this project."
      PARENT_SCOPE
    )
    return()
  endif()

  set("${ARG_OUTPUT_VARIABLE}" TRUE PARENT_SCOPE)
  set("${ARG_ERROR_VARIABLE}" "" PARENT_SCOPE)
endfunction()

besa_register_feature_constraint(
  FUNCTION no_cuda_and_hip
)
```

BESA invokes the function with `OUTPUT_VARIABLE`, `ERROR_VARIABLE`, and `FEATURES`.

## Devtool constraints

A project can impose policy on BESA-defined devtools without redefining which devtools BESA
supports:

```cmake
function(no_asan_with_coverage)
  besa_devtool_constraint_arguments_parse(
    PREFIX ARG
    ARGUMENTS ${ARGN}
  )

  if("asan" IN_LIST ARG_DEVTOOLS
     AND "coverage" IN_LIST ARG_DEVTOOLS)
    set("${ARG_OUTPUT_VARIABLE}" FALSE PARENT_SCOPE)
    set(
      "${ARG_ERROR_VARIABLE}"
      "This project does not support ASan and coverage in the same build."
      PARENT_SCOPE
    )
    return()
  endif()

  set("${ARG_OUTPUT_VARIABLE}" TRUE PARENT_SCOPE)
  set("${ARG_ERROR_VARIABLE}" "" PARENT_SCOPE)
endfunction()

besa_register_devtool_constraint(
  FUNCTION no_asan_with_coverage
)
```

The callback receives `OUTPUT_VARIABLE`, `ERROR_VARIABLE`, and `DEVTOOLS`.

## Test-mode constraints

Test-mode constraints are available for projects whose test workflows have incompatible
combinations:

```cmake
function(no_commit_with_nightly)
  besa_test_mode_constraint_arguments_parse(
    PREFIX ARG
    ARGUMENTS ${ARGN}
  )

  if("ci-commit" IN_LIST ARG_MODES
     AND "nightly" IN_LIST ARG_MODES)
    set("${ARG_OUTPUT_VARIABLE}" FALSE PARENT_SCOPE)
    set(
      "${ARG_ERROR_VARIABLE}"
      "ci-commit and nightly are separate test workflows."
      PARENT_SCOPE
    )
    return()
  endif()

  set("${ARG_OUTPUT_VARIABLE}" TRUE PARENT_SCOPE)
  set("${ARG_ERROR_VARIABLE}" "" PARENT_SCOPE)
endfunction()

besa_register_test_mode_constraint(
  FUNCTION no_commit_with_nightly
)
```

The callback receives `OUTPUT_VARIABLE`, `ERROR_VARIABLE`, and `MODES`.

## Complete configuration after registration

Register every constraint before the configuration phase is closed:

```cmake
besa_register_feature_constraint(FUNCTION no_cuda_and_hip)
besa_register_devtool_constraint(FUNCTION no_asan_with_coverage)
besa_register_test_mode_constraint(FUNCTION no_commit_with_nightly)

besa_configure_complete()
```

If a callback sets its output variable to false, BESA reports the callback-provided error with
`message(FATAL_ERROR)`. A false result with no error text still rejects the configuration with a
generic constraint diagnostic.
