<!--
--------------------------------------------------------------------------------------------------
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 besa developers
--------------------------------------------------------------------------------------------------
-->
# Test projects as examples

Every fixture is a small project using the public BESA API. Following the Nola project
pattern, **each project owns `cmake/options.cmake`**. That file declares normal CMake cache
variables, registers metadata with `besa_register_options()`, and calls
`besa_finalize_options()` once. The main `CMakeLists.txt` includes the file immediately after
`find_package(besa CONFIG REQUIRED)`, before creating libraries, executables, or tests.

The test driver overrides only the project-declared options (`BUILD_DEVTOOLS`, `BUILD_WARNINGS`,
`TEST_MODE`, `PROJECT_FEATURE`, `RELEASE_TYPE`, etc.). No test-specific `SANITIZER`,
`SURROGATE_BROKEN`, or `EXPECT_MERGE_TESTS` selector is accepted. Test directories may be
registered conditionally based on resolved options. For example:

```cmake
# cmake/options.cmake
set(BUILD_DEVTOOLS "none" CACHE STRING "Enabled development tools")
besa_register_options(GROUP build VARIABLES BUILD_DEVTOOLS)
besa_finalize_options()
```

```cmake
# CMakeLists.txt, after include(cmake/options.cmake)
foreach(_sanitizer IN ITEMS asan ubsan)
  besa_devtools_check(OUTPUT_VARIABLE _enabled DEVTOOLS "${_sanitizer}")
  if(_enabled)
    besa_test_add_directory(NAME "${_sanitizer}" PREFIX sanitizers)
  endif()
endforeach()
```

Test-directory `MODES` and `CONDITION` still describe which declared test modes and features
support a test, rather than adding options to configure. The same distinction applies to the
source tree and build options.

For intentionally invalid usage, create a dedicated small negative fixture rather than an `if()`
branch enabled by an undocumented `-D` test flag. CMake assertions that must not clutter a normal
example may remain in `test.cmake`, injected with `CMAKE_PROJECT_INCLUDE`. Assertions for generated
files belong in `check-*.cmake`. In `ARGS` the driver expands `@BINARY_DIR@` and `@SOURCE_DIR@`
so the harness can configure real file-valued BESA options directly.

This keeps examples copyable and makes every configuration knob traceable to a declared capability
or public BESA option.
