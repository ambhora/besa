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

Project-feature logic belongs in the portable model rather than in a CMake callback. Declare the
complete feature domain and a Python evaluator in `besa.toml`:

```toml
[[constraints]]
name = "no-cuda-and-hip"
features = ["toolchain-cuda", "toolchain-hip"]
callback = "tools/constraints.py:no_cuda_and_hip"
```

The callback receives one dictionary whose `features` member maps every declared input feature to a
boolean:

```python
def no_cuda_and_hip(context):
    features = context["features"]
    valid = not (features["toolchain-cuda"] and features["toolchain-hip"])
    return {
        "success": True,
        "result": valid,
        "reason": "CUDA and HIP cannot be enabled together." if not valid else "",
    }
```

BESA evaluates the finite domain of this function, stores its truth table below
`<workspace>/configure_cache/constraints/`, and uses that same result for the CMake backend and API
configuration-space analysis. The cache is invalidated when the constraint declaration or callback
implementation changes.

`success = false` means evaluation itself failed and is a configuration error. `success = true` with
`result = false` means the examined feature assignment is invalid. A bare boolean return is also
accepted for simple predicates.

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

## Complete configuration

`besa_model_realize()` translates portable feature constraints into the CMake backend before it
closes the configuration phase. Backend-specific devtool and test-mode constraints must still be
registered before `besa_configure_complete()` in custom CMake code.

A rejected configuration stops configuration before compiler-dependent project structure is
realized.
