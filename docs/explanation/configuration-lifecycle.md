<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Configuration lifecycle

BESA deliberately separates configuration selection from project construction.

Before `besa_configure_complete()`, the project declares the configuration sets which it owns:
features, default features, test modes, and default test modes. It may also register feature,
devtool, and test-mode constraints. Devtool and warning capability names themselves are supplied by
BESA, so projects select them but do not redeclare their allow-lists.

`besa_configure_complete()` then resolves four independent families:

1. `PROJECT_FEATURES` over the project's feature defaults;
2. `PROJECT_DEVTOOLS` over BESA's supported devtools;
3. `TEST_MODES` over the project's test-mode defaults;
4. `PROJECT_WARNINGS` over BESA's supported warning policies.

Duplicate or unknown selections are rejected first. Project constraints run against the fully
resolved feature/devtool/test-mode sets next. Only after every constraint succeeds does BESA publish
the resolved booleans, enable compiler languages implied by `toolchain-*`, and create any
compiler-dependent instrumentation policy.

After this phase boundary, dependencies, directories, targets, and tests are processed against a
frozen configuration. This prevents a dependency or subdirectory from implicitly changing the
meaning of configuration selection halfway through a configure run.

Project-wide packaging and instrumentation reporting need the final target/dependency graph. BESA
therefore schedules those operations with CMake's deferred-call mechanism and executes them after the
project tree has been processed.
