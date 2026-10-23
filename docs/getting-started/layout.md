# Project layout at a glance

BESA gives meaning to a handful of directory names. Nothing else about the
layout is prescribed: you choose where units live and what they are called.

## A source unit

A **source unit** is any directory passed as `ROOT` to
`besa_add_directory()` (or `DIRECTORY` to `besa_add_subdirectory()`). BESA
looks for these subdirectories inside it:

| Subdirectory | Contents | Becomes |
| --- | --- | --- |
| `include/` | Public headers, any depth | `FILE_SET HEADERS` with `include/` as the base directory; a `PUBLIC` (or `INTERFACE`) include path |
| `lib/` | Implementation files, any depth | `PRIVATE` sources compiled in the unit's declared language |
| `module/` | C++ module interface units (`TYPE cpp` only) | `FILE_SET CXX_MODULES`, public |
| `mod/` | Fortran module sources (`TYPE fortran` only) | `PRIVATE` sources |

All four are optional. A unit with only `include/` is a header-only unit; a
unit with only `lib/` adds private implementation to a library whose public
interface comes from another unit.

**The file extension never determines the language.** Everything under
`lib/` is compiled as the unit's `TYPE`, so `implementation.custom` in a
`cpp` unit is compiled as C++. This is deliberate: the semantic type is
declared once, in the build description, not inferred file by file.

## Built-in unit types

| `TYPE` | CMake language enabled | Notes |
| --- | --- | --- |
| `c` | `C` | |
| `cpp` | `CXX` | May contain `module/` |
| `cuda` | `CUDA` | |
| `hip` | `HIP` | |
| `fortran` | `Fortran` | May contain `mod/` |
| `bin` | *none* | Executables; see below |

Projects can register additional *generated* types that resolve to one of
the built-ins. See [Generated source](../guide/code-generation.md).

## The `bin` type

`besa_add_subdirectory(DIRECTORY <dir> TYPE bin)` creates **one executable
per regular file directly inside `<dir>`**. The target name is the file name
without its last extension: `bin/greet-cli.cpp` → `greet-cli`.

`bin` units are intentionally minimal:

- no language is enabled — CMake infers it from the sources and the
  languages other units already enabled;
- no library is linked — add `target_link_libraries()` yourself;
- subdirectories of `<dir>` are ignored;
- every executable is registered for installation.

## Tests

`besa_test_add_directory(NAME <dir>)` scans `<dir>` recursively for files
matching `*.t.{c,cc,cpp,cxx,cu}`:

| File | Test property |
| --- | --- |
| `name.t.cpp` | Ordinary test |
| `name.fail.t.cpp` | `WILL_FAIL TRUE` |
| `name.disabled.t.cpp` | `DISABLED TRUE` |
| `name.disabled.fail.t.cpp` | Both |
| `name/` (a directory next to `name.t.cpp`) | Extra sources compiled into that one test |

Files that do not match the pattern are ignored, so helpers and data can
live alongside the tests. See [Tests](../guide/testing.md).

## The options file

By convention, user-facing cache variables live in `cmake/options.cmake`,
which ends with `besa_finalize_options()` and is included immediately after
`find_package(besa)`. BESA does not enforce the file name — only the order:
declare, finalize, then create targets.

## BESA's own files in the build tree

BESA keeps everything it writes under one directory:

```text
build/besa/
├── manifest.json            # the semantic manifest
├── codegen/                 # generated source trees, incl. meta/include/<project>/version.hpp
├── docs/                    # outputs of besa_add_cpdocs_docs()/besa_add_user_docs()
├── configure_cache/         # reserved for configure-time caches
├── package/                 # generated <Project>Config.cmake etc., staged for install
└── subdirectories/<unit>/   # per-unit scratch space handed to generator callbacks
```

`BESA_WORKSPACE` relocates the whole tree if you need it elsewhere.

## Putting it together

A larger project might look like this:

```text
myproject/
├── CMakeLists.txt
├── cmake/options.cmake
├── core/                  # besa_add_directory(LIBRARY libcore ROOT core TYPE cpp)
│   ├── include/myproject/core/...
│   ├── lib/...
│   └── module/...
├── gpu/                   # besa_add_directory(LIBRARY libcore ROOT gpu TYPE cuda CONDITION gpu)
│   ├── include/myproject/gpu/...
│   └── lib/...
├── schema/                # besa_add_directory(LIBRARY libcore ROOT schema TYPE jnum)  (generated)
├── tools/                 # besa_add_subdirectory(DIRECTORY tools TYPE bin)
└── tests/
    ├── unit/              # besa_test_add_directory(NAME unit ...)
    └── gpu/               # besa_test_add_directory(NAME gpu CONDITION gpu ...)
```

Two units of different languages feed one library; one of them is selected
by a feature; a third is produced by a code generator; tests for the GPU path
exist only when the `gpu` feature is on.
