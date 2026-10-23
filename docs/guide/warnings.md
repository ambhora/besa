# Warning policies

`BUILD_WARNINGS` selects a compiler-warning policy for every BESA-managed
target. Like devtools, the policies are BESA capabilities: projects pick
one, they do not define their own flag lists.

```bash
cmake -B build -DBUILD_WARNINGS=minimal          # the default
cmake -B build -DBUILD_WARNINGS="extra;werror"
cmake -B build -DBUILD_WARNINGS=everything
cmake -B build -DBUILD_WARNINGS=none
```

## Policies

Three **levels** form an increasing scale; at most one may be selected.
`werror` is independent and combines with any level. `none` disables all
policies and must stand alone.

| Policy | GCC / Clang (C, C++) | NVIDIA CUDA | Includes |
| --- | --- | --- | --- |
| `minimal` | `-Wall` | `-Xcompiler=-Wall` | — |
| `extra` | `-Wextra -Wpedantic -Wdeprecated` | `-Xcompiler=-Wextra,-Wpedantic` | `minimal` |
| `everything` | Clang: `-Weverything -Wno-padded`, and for C++ also `-Wno-c++98-compat -Wno-c++98-compat-pedantic -Wno-weak-vtables`; GCC: nothing beyond `extra` | — | `extra` |
| `werror` | `-Werror` | — | — |

Each policy is an `INTERFACE` target (`besa::warning.minimal`,
`besa::warning.extra`, `besa::warning.everything`, `besa::warning.werror`)
whose options are guarded by `$<COMPILE_LANG_AND_ID:...>`, so unknown
compilers see no flags at all. BESA links its targets to the selected
policies `PRIVATE` through `$<BUILD_INTERFACE:...>`; nothing is exported.

## Which targets are affected

Every target created through BESA: libraries from `besa_add_library()`,
executables from `bin` units and `besa_add_executable()`, discovered tests
and compile tests. Targets you create with plain `add_library()` or
`add_executable()` are not touched. If you want one of them to follow the
project policy, link it to the policy targets yourself:

```cmake
add_executable(bench bench.cpp)
target_link_libraries(bench PRIVATE besa::warning.extra besa::warning.werror)
```

## Testing a policy

A `warnings` fixture in the BESA repository demonstrates the intended use:
a source file with an unused variable builds cleanly under `minimal` and
fails under `extra;werror`. Enforce `werror` in CI, keep it off by default
so a new compiler's new warnings do not break every developer's build.

## Published variables

`BESA_ENABLED_WARNINGS` holds the selected list; `BUILD_WARNINGS_MINIMAL`,
`BUILD_WARNINGS_EXTRA`, `BUILD_WARNINGS_EVERYTHING` and
`BUILD_WARNINGS_WERROR` are booleans.

## Compatibility

Older projects that set `PROJECT_WARNINGS` instead of `BUILD_WARNINGS`
continue to work; the legacy spellings `essential` and `error` are mapped to
`extra` and `werror`.
