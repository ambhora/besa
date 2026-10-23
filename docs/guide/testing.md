# Tests

BESA discovers tests from the file system. A file is a test because of its
name, not because a `CMakeLists.txt` lists it; adding a test means adding a
file. Expectations such as "this must fail" or "this is disabled" are part
of the name too, so they are visible in a directory listing and in `ctest`
output alike.

## Runtime tests

```cmake
besa_test_add_directory(
  NAME <dir>
  [PREFIX <prefix>]
  [TARGET_LIST <targets>...]
  [LABELS <labels>...]
  [CMDLINE <arguments>...]
  [CONDITION <feature-space>]
  [MODES <test-modes>...]
  [DEVTOOLS <devtools>...]
  [COVERAGE_GROUP <group>]
)
```

`NAME` is a directory relative to the current source directory. It is
scanned **recursively** for files matching `*.t.{c,cc,cpp,cxx,cu}`. For each
match BESA creates an executable (not installed), links it `PRIVATE` to
every target in `TARGET_LIST`, applies the project's warning and devtool
policies, and registers a CTest test that runs it with `CMDLINE`.

### Naming

The test and target name is the file's path relative to `NAME`, without the
last extension, with `/` turned into `.`, and `PREFIX.` prepended:

| File under `tests/` | `PREFIX greet` → test name |
| --- | --- |
| `greet.t.cpp` | `greet.greet.t` |
| `parser/tokens.t.cpp` | `greet.parser.tokens.t` |
| `io/read.fail.t.cpp` | `greet.io.read.fail.t` |

Because the target name is the test name, choose a `PREFIX` that is unique
within the project when several directories are registered.

### Expectations encoded in the name

| Suffix | CTest property |
| --- | --- |
| `.t.cpp` | — |
| `.fail.t.cpp` | `WILL_FAIL TRUE` — the test passes when the executable exits non-zero |
| `.disabled.t.cpp` | `DISABLED TRUE` — built and registered, reported as "Not Run" |
| `.disabled.fail.t.cpp` | both |

`.fail.` is the natural way to test sanitizers: an `overflow.fail.t.cpp`
that reads past an array is expected to be killed by AddressSanitizer, so it
passes with `asan` and fails without it. `.disabled.` keeps a known-broken
test compiling while it is fixed.

### Multi-file tests

A test may have a companion directory with the same stem. Everything under
it is compiled into that test and nothing else:

```text
tests/
├── greet.t.cpp
└── greet/
    └── report.cpp      # linked into greet.greet.t only
```

Files that do not match the test pattern — fixtures, data, helpers in the
companion directory — are otherwise ignored, so the test tree can be
organized freely.

### Labels and arguments

`LABELS` are set on every discovered test (`ctest -L unit`). `CMDLINE` is
appended to every command line, which is convenient for test frameworks that
take a reporter flag.

## Compile-only tests

```cmake
besa_compile_test_add_directory(
  NAME <dir> [PREFIX <prefix>] [TARGET_LIST <targets>...] [LABELS <labels>...]
  [CONDITION <space>] [MODES <modes>...] [DEVTOOLS <devtools>...]
)
```

Same discovery and naming, different meaning: the test **is the build**.
Each file becomes an `EXCLUDE_FROM_ALL` executable, and the CTest test runs
`cmake --build <build> --target <test>`. The suffix rules apply, so
`rejects.fail.t.cpp` passes only if it *fails to compile* — ideal for
checking that a `static_assert` fires, a constraint is not satisfied, or an
overload is deleted:

```cpp
// checks/rejects.fail.t.cpp
#include <core/strong.hpp>
int main() { core::metres m = 3; }   // implicit conversion must not compile
```

Compile tests are never built by the default target, so they cost nothing
unless `ctest` runs them.

## Selecting test directories

Three optional arguments decide whether a directory is registered at all.
They are **predicates on the resolved configuration** — the same
configuration the user selected through the project's options — not new
options of their own.

`CONDITION <space>`
:   Register only when the [feature space](feature-spaces.md) matches the
    enabled features (subset matching). `CONDITION gpu` registers the
    directory in GPU builds.

`MODES <mode>...`
:   Register only when at least one of the listed [test modes](test-modes.md)
    is enabled. Names must be declared modes; `~mode` is not allowed here.

`DEVTOOLS <devtool>...`
:   Register only when at least one of the listed
    [devtools](devtools.md) is enabled.

```cmake
besa_test_add_directory(NAME unit      PREFIX unit  TARGET_LIST core::libcore MODES commit merge)
besa_test_add_directory(NAME slow      PREFIX slow  TARGET_LIST core::libcore MODES merge)
besa_test_add_directory(NAME gpu       PREFIX gpu   TARGET_LIST core::libcore CONDITION gpu)
besa_test_add_directory(NAME sanitizer PREFIX san   TARGET_LIST core::libcore DEVTOOLS asan ubsan)
```

The checks are evaluated in order: an unmatched `CONDITION` skips the
directory immediately; a matched one still validates every name in `MODES`
and `DEVTOOLS`, so typos are caught in every configuration.

The equivalent `if()` form is also fine when more logic is needed:

```cmake
besa_devtools_check(OUTPUT_VARIABLE WITH_ASAN DEVTOOLS asan)
if(WITH_ASAN)
  besa_test_add_directory(NAME asan PREFIX sanitizers)
endif()
```

## Coverage groups

With the `coverage` devtool enabled, `COVERAGE_GROUP <group>` assigns the
directory's tests to a named group. BESA creates a report target and a
report test per group, and an aggregate `instrumentation.coverage.t` that
depends on them all. See [Developer tools](devtools.md#coverage).

## Tests BESA adds on its own

Some devtools register tests during finalization. They are labelled
`instrumentation` so you can include or exclude them with `ctest -L` / `-LE`:

| Test | Created when | Labels |
| --- | --- | --- |
| `instrumentation.format.t` | `BUILD_DEVTOOLS` contains `format` | `instrumentation format` |
| `instrumentation.linting.t` | `BUILD_DEVTOOLS` contains `linting` | `instrumentation linting` |
| `instrumentation.coverage.<group>.t`, `instrumentation.coverage.t` | `coverage` and at least one `COVERAGE_GROUP` | `instrumentation coverage` |
| `surrogate.<library>.t` | `surrogate`, per non-interface library | `instrumentation surrogate` |

All of them require `BUILD_TESTING` to be on.

## A typical layout

```text
tests/
├── unit/                  # besa_test_add_directory(NAME unit PREFIX unit MODES commit merge)
│   ├── parser.t.cpp
│   ├── parser/
│   │   └── samples.cpp
│   └── io.disabled.t.cpp
├── slow/                  # besa_test_add_directory(NAME slow PREFIX slow MODES merge)
│   └── stress.t.cpp
├── compile/               # besa_compile_test_add_directory(NAME compile PREFIX compile)
│   ├── accepts.t.cpp
│   └── rejects.fail.t.cpp
└── sanitizers/            # besa_test_add_directory(NAME sanitizers PREFIX san DEVTOOLS asan ubsan)
    └── overflow.fail.t.cpp
```

```bash
ctest --test-dir build                       # everything registered for this configuration
ctest --test-dir build -R '^unit\.'          # one directory
ctest --test-dir build -LE instrumentation   # skip format/lint/coverage/surrogate
```
