# Selector reference

Selectors are conditions evaluated against the **resolved enabled feature set**. They are accepted as
values of a public function's named `WHEN` argument. Selector evaluation is available only after
`besa_configure_complete()` has frozen configuration.

## `ALL_OF`

```cmake
WHEN ALL_OF feature-a feature-b ~feature-c
```

Every atom must match. A normal atom matches when that feature is enabled; a `~feature` atom matches
when that feature is disabled. The same underlying feature must not appear twice in one selector.

## `ANY_OF`

```cmake
WHEN ANY_OF toolchain-cuda toolchain-hip
```

At least one atom must match. Negated atoms use the same semantics as `ALL_OF`.

## `REGEX`

```cmake
WHEN REGEX "^project-"
```

The selector succeeds when at least one enabled feature matches the CMake regular expression. This
is intentionally regex syntax, not glob syntax. It is useful for namespace-like feature families
such as `project-*` and `showcase-*` without introducing wildcard parsing rules into BESA.

## `FUNCTION`

```cmake
WHEN FUNCTION my_selector
```

BESA invokes the named CMake command using this contract:

```cmake
my_selector(
  OUTPUT_VARIABLE <variable-to-set>
  ERROR_VARIABLE  <variable-to-set>
  NAME            <object-name>
  FEATURES        <resolved-feature>...
)
```

Use the public parser helper rather than duplicating callback argument parsing:

```cmake
function(my_selector)
  besa_selector_arguments_parse(
    PREFIX ARG
    ARGUMENTS ${ARGN}
  )

  # ARG_NAME is the object being considered.
  # ARG_FEATURES is the resolved enabled feature list.

  set("${ARG_OUTPUT_VARIABLE}" TRUE PARENT_SCOPE)
  set("${ARG_ERROR_VARIABLE}" "" PARENT_SCOPE)
endfunction()
```

Set the output to `FALSE` with an empty error to mean "not selected". Set `ERROR_VARIABLE` to a
non-empty string only when evaluation itself is invalid; BESA reports that text as a fatal
configuration error.
