# Developer tools

`BUILD_DEVTOOLS` is a single cache variable that selects instrumentation
and quality tooling for a build. The catalog of tools is owned by BESA.
Projects choose from it; they never write sanitizer flags, coverage
plumbing or clang-tidy invocations themselves — and when BESA gains a tool,
every project gets it by updating BESA.

```bash
cmake -B build -DBUILD_DEVTOOLS="asan;ubsan"
cmake -B build -DBUILD_DEVTOOLS="coverage"
cmake -B build -DBUILD_DEVTOOLS="format;linting;surrogate"
cmake -B build -DBUILD_DEVTOOLS=none            # the default
```

Values may be combined freely except that `none` must stand alone. Unknown
names fail configuration with the list of allowed values.

| Devtool | Kind | Effect |
| --- | --- | --- |
| `asan` | compiler | AddressSanitizer on every BESA-managed target |
| `lsan` | compiler | LeakSanitizer |
| `ubsan` | compiler | UndefinedBehaviorSanitizer |
| `coverage` | compiler + tests | Coverage instrumentation, grouped reports |
| `surrogate` | tests | Compile every public header in isolation |
| `format` | tests | `clang-format --dry-run` over the source tree |
| `linting` | tests | `run-clang-tidy` over the compilation database |

"Compiler" devtools change how targets are compiled and linked. "Tests"
devtools add CTest tests during finalization (and therefore need
`BUILD_TESTING=ON` to show up).

## How instrumentation reaches targets

Each compiler devtool is an `INTERFACE` target — `besa::asan`, `besa::lsan`,
`besa::ubsan`, `besa::coverage` — carrying compile and link options behind
`$<COMPILE_LANG_AND_ID:...>` generator expressions. BESA links every target
it creates to the selected ones with `PRIVATE $<BUILD_INTERFACE:...>`, so:

- all BESA libraries, `bin` executables, hand-declared `besa_add_executable()`
  targets and discovered tests are instrumented consistently;
- nothing leaks into the installed package or its exported targets;
- targets you create with plain `add_library()` are untouched — link them to
  `besa::asan` yourself if you want them included.

The flags themselves:

| Target | Compile | Link |
| --- | --- | --- |
| `besa::asan` | `-fsanitize=address -fno-sanitize-recover=address -fno-omit-frame-pointer -fno-optimize-sibling-calls -fsanitize-address-use-after-scope` | `-fsanitize=address -fno-sanitize-recover=address` |
| `besa::lsan` | `-fsanitize=leak -fno-omit-frame-pointer` | `-fsanitize=leak` |
| `besa::ubsan` | `-fsanitize=undefined -fno-sanitize-recover=undefined -fno-omit-frame-pointer` | `-fsanitize=undefined -fno-sanitize-recover=undefined` |
| `besa::coverage` (Clang) | `-fprofile-instr-generate -fcoverage-mapping` | same |
| `besa::coverage` (GCC) | `--coverage -fprofile-abs-path` | `--coverage` |

Sanitizer flags apply to C and C++ with GCC and Clang; other compilers
simply see no flags. `-fno-sanitize-recover` is deliberate: a detected error
aborts the test, so a `.fail.t.cpp` that triggers it passes.

## Sanitizers

Nothing to configure beyond the selection. A typical pattern is a test
directory that exists only in instrumented builds:

```cmake
besa_test_add_directory(NAME sanitizers PREFIX san TARGET_LIST core::libcore DEVTOOLS asan ubsan)
```

```cpp
// sanitizers/overflow.fail.t.cpp — passes only when asan catches it
int main() { int a[4] = {}; volatile int i = 4; return a[i]; }
```

!!! note "Kernel ASLR and older sanitizer runtimes"
    On recent Linux kernels, sanitizers from older toolchains may fail to
    start because the kernel uses more address-space randomization bits than
    the runtime expects. BESA's own CI lowers it with
    `sysctl -w vm.mmap_rnd_bits=28`; the same workaround applies to any
    project.

## Coverage

Enable with `coverage` and assign tests to **groups**:

```cmake
besa_test_add_directory(NAME tests PREFIX unit TARGET_LIST core::libcore COVERAGE_GROUP unit)
besa_test_add_directory(NAME integ PREFIX integ TARGET_LIST core::libcore COVERAGE_GROUP integration)
```

For each group BESA creates:

- a build target `besa.coverage.<group>` that produces the report;
- a test `instrumentation.coverage.<group>.t` that builds that target and
  `DEPENDS` on every test in the group, so CTest orders them correctly.

Plus an aggregate target `besa.coverage` and test `instrumentation.coverage.t`
covering all groups. Reports land in `BESA_COVERAGE_OUTDIR` (default
`build/coverage/<group>/`):

| Compiler | Tools | Outputs |
| --- | --- | --- |
| Clang | `llvm-profdata`, `llvm-cov` | `summary.txt`, `coverage.json`, `html/`, merged `coverage.profdata`; raw profiles in `prof/` (one per test via `LLVM_PROFILE_FILE`) |
| GCC | `gcovr` | `summary.txt`, `summary.json`, `cobertura.xml`, `index.html` with details |

A complete coverage run is therefore just `ctest`:

```bash
cmake -B build -DBUILD_DEVTOOLS=coverage -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build                 # runs tests, then builds the reports
open build/coverage/unit/index.html    # GCC; build/coverage/unit/html/ for Clang
```

Coverage requires a GCC or Clang C/C++ toolchain; other compilers fail
configuration with a clear message. Tests without a `COVERAGE_GROUP` are
still instrumented but do not contribute to a report.

## Surrogate: public header checks

`surrogate` answers "does every public header compile on its own?". For
each non-interface library created with `besa_add_library()`, BESA registers
`surrogate.<library>.t`. The test builds a hidden library whose sources are
generated one-per-header:

```cpp
// build/surrogate/libcore/core/parser.hpp.cpp
#include <core/parser.hpp>
```

The translation unit's language is the one *declared for the unit that owns
the header* — a header in a `TYPE c` unit is checked as C, in a `TYPE cuda`
unit as CUDA — never guessed from the extension. For include directories
that did not come from `besa_add_directory()`, BESA uses the single enabled
compilable language if there is exactly one, and refuses to guess otherwise.

Discovery runs deferred, at the end of configuration, so units attached
after `besa_add_library()` (the normal case) are included.

You can also register checks explicitly, for example to assert that a
header is *supposed* to be broken in a negative test:

```cmake
besa_surrogate_check(TARGET libexperimental EXPECT FAIL LABELS experimental)
```

A passing surrogate check is a strong signal, not a proof: it does not
exercise every header combination or generator-expression context.

## Format

`format` registers `instrumentation.format.t`, which runs
`clang-format --dry-run -Werror --style=file` on every file in the source
tree with one of these extensions:

```text
.c .h .cc .cpp .cxx .hh .hpp .hxx .cu .cuh .cuhpp .m .mm .proto .json
```

`build/`, `.git/` and `.venv/` directories (anywhere in the tree) are
skipped. The test fails listing every offending file. Place a
`.clang-format` at the project root as usual; BESA does not supply a style.

The underlying command is `besa_add_clang_format(NAME <test> [LABELS ...])`,
available directly if you want additional or differently labelled runs.

## Linting

`linting` registers `instrumentation.linting.t`, which runs
`run-clang-tidy -clang-tidy-binary <clang-tidy> -p <build>` from the source
root, so clang-tidy sees real translation units with real flags.
`besa_finalize_options()` already turns on `CMAKE_EXPORT_COMPILE_COMMANDS`,
so the compilation database is always present. A `.clang-tidy` at the
project root selects the checks.

For custom invocations use `besa_add_clang_tidy(NAME <test> [LABELS ...]
[ARGUMENTS ...])`; `ARGUMENTS` are forwarded verbatim (file filters,
`-fix`, `-quiet`, …).

## Querying the selection

```cmake
besa_devtools_check(OUTPUT_VARIABLE <var> [DEVTOOLS <name>...])
```

`TRUE` when any of the listed devtools is enabled (or when none are listed).
Unknown names are errors. The booleans `BUILD_DEVTOOLS_ASAN`,
`BUILD_DEVTOOLS_COVERAGE`, … and the list `BESA_ENABLED_DEVTOOLS` are also
published.

## Constraining combinations

Projects may veto devtool sets with a constraint callback registered before
finalization; see [Custom validation](options.md#custom-validation). BESA
itself imposes no restrictions beyond `none` being exclusive, so combining
`asan` and `lsan`, or `coverage` with a sanitizer, is up to the project and
the toolchain.
