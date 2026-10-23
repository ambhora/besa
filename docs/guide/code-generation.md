# Generated source

Some source is produced by a tool at build time: bindings from an IDL,
tables from a schema, kernels from a template. BESA lets a project register
a **generated unit type** so that generated trees are declared, lowered,
installed and documented exactly like hand-written ones.

```cmake
besa_add_directory(LIBRARY libcore ROOT schema TYPE jnum)
```

From the project's point of view `jnum` is just another `TYPE`. What makes
it work is a small callback registered beforehand.

## Registering a generated type

```cmake
besa_register_subdirectory_type(<type> GENERATED FUNCTION <callback> RESOLVES_TO <builtin-type>)
```

Call it in the open phase, before `besa_finalize_options()`. The three
pieces:

`<type>`
:   The name projects will write after `TYPE`. Must not clash with a
    built-in or previously registered type.

`RESOLVES_TO`
:   The built-in type (`c`, `cpp`, `cuda`, `hip`, `fortran`) the generated
    tree conforms to. It decides which language is enabled and how the
    output tree is lowered. `bin` is not a valid resolution.

`FUNCTION`
:   A CMake command that populates an output directory with a tree in the
    `RESOLVES_TO` layout (`include/`, `lib/`, and `mod/` for Fortran).

`GENERATED` is currently required: every custom type is a generated type.

## The callback contract

BESA calls the function with named arguments:

| Argument | Meaning |
| --- | --- |
| `SOURCE_DIR` | Absolute path of the `ROOT` the project passed — the generator's inputs |
| `BUILD_DIR` | A private scratch directory for this unit under `build/besa/subdirectories/` |
| `OUTPUT_DIR` | Where the generated tree must go. BESA pre-creates `include/` and `lib/` (and `mod/` for Fortran) |
| `OUTPUT_TARGET_VARIABLE` | Name of a variable to set (in `PARENT_SCOPE`) to the target that performs generation, if any |
| *anything in `ARGS`* | Forwarded verbatim from `besa_add_directory(... ARGS ...)` |

A complete example, adapted from BESA's `generated` fixture:

```cmake
function(jnum_add_subdirectory)
  cmake_parse_arguments(ARG "" "SOURCE_DIR;BUILD_DIR;OUTPUT_DIR;OUTPUT_TARGET_VARIABLE;LINK_TYPE" "" ${ARGN})

  # Configure-time generation: write the tree directly.
  file(MAKE_DIRECTORY "${ARG_OUTPUT_DIR}/include/generated")
  file(WRITE "${ARG_OUTPUT_DIR}/include/generated/table.hpp"
    "#pragma once\nnamespace generated { int answer(); }\n")
  file(WRITE "${ARG_OUTPUT_DIR}/lib/table.cpp"
    "#include <generated/table.hpp>\nnamespace generated { int answer() { return 42; } }\n")

  # Build-time generation: a target that regenerates when inputs change.
  add_custom_command(
    OUTPUT "${ARG_BUILD_DIR}/codegen.stamp"
    COMMAND jnum-compile "${ARG_SOURCE_DIR}/input.jnum" --out "${ARG_OUTPUT_DIR}"
    COMMAND "${CMAKE_COMMAND}" -E touch "${ARG_BUILD_DIR}/codegen.stamp"
    DEPENDS "${ARG_SOURCE_DIR}/input.jnum"
    VERBATIM
  )
  add_custom_target(jnum.generate DEPENDS "${ARG_BUILD_DIR}/codegen.stamp")
  set("${ARG_OUTPUT_TARGET_VARIABLE}" jnum.generate PARENT_SCOPE)
endfunction()

besa_register_subdirectory_type(jnum GENERATED FUNCTION jnum_add_subdirectory RESOLVES_TO cpp)
include(cmake/options.cmake)

besa_add_library(NAME libcore TYPE STATIC)
besa_add_directory(LIBRARY libcore ROOT schema TYPE jnum ARGS LINK_TYPE STATIC)
```

Generators may work at configure time (writing files directly), at build
time (through the returned target), or both. The split in the example is
typical: write enough at configure time for CMake to know the file list,
and regenerate at build time when inputs change.

## What BESA does with the result

After the callback returns, BESA:

1. **Registers the unit in the manifest** with `"generated": true`, the
   resolved `type`, and the custom name under `"source-type"`.
2. **Enables the resolved language** if needed.
3. **Lowers `OUTPUT_DIR`** exactly like a hand-written unit of the resolved
   type: `include/` becomes a public header file set, `lib/` becomes
   private sources in the declared language.
4. If a target was returned, **wires it into CMake's `codegen` target** via
   a `CODEGEN` custom command and makes the library depend on it, so
   `cmake --build build --target codegen` produces every generated tree
   without compiling anything.

Generated output always lives under `BESA_CODEGEN_DIRECTORY`
(`build/besa/codegen/<unit>/`), never in the source tree. `ROOT` for a
generated unit is the *input* directory; it need not contain `include/` or
`lib/` itself.

## Why `codegen` matters

The reserved `codegen` target (CMake ≥ 3.31) is what lets tools look at
generated API without a full build. cpdocs, for instance, builds `codegen`
on the host and then reads the generated `include/` roots listed in the
manifest. BESA's `besa.cpdocs` target depends on every generator target for
the same reason. See [Documentation targets](documentation.md).

## Conditions and arguments

`CONDITION` and `ARGS` work for generated units as for built-in ones:

```cmake
besa_add_directory(LIBRARY libcore ROOT kernels TYPE kgen CONDITION gpu ARGS ARCH sm_90)
```

When the condition does not match, the callback is not invoked and nothing
is generated.
