<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Test projects as examples

The `CMakeLists.txt` files in this directory are intentionally written as small, realistic examples
of BESA usage. Test-only assertions and negative-test mutations do not belong in those files.

When a project needs configure-time test logic, put it in `test.cmake`. The test driver loads that
file through `CMAKE_PROJECT_INCLUDE`, so it can schedule deferred assertions without changing the
example project itself. Checks that only need generated files should remain in `check-*.cmake` and
run after configuration.

This convention keeps the test suite useful as executable documentation: opening a project's
`CMakeLists.txt` should show the normal BESA API, not the machinery used to test it.
