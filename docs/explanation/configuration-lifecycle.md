<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Configuration lifecycle

BESA deliberately separates configuration selection from project construction.

The portable project-owned configuration model lives in `besa.toml`: features and their defaults,
test modes, API profiles, dependencies, project topology, and portable feature constraints. The CMake
backend loads that model and translates it into BESA's internal registries. Devtool and warning
capability names remain backend capabilities supplied by BESA rather than project declarations.

`besa_configure_complete()` then resolves four independent families:

1. `PROJECT_FEATURES` over the project's feature defaults;
2. `PROJECT_DEVTOOLS` over BESA's supported devtools;
3. `TEST_MODES` over the project's test-mode defaults;
4. `PROJECT_WARNINGS` over BESA's supported warning policies.

Duplicate or unknown selections are rejected first. Portable feature constraints and any backend-specific
devtool/test-mode constraints run against the fully resolved sets next. Only after every constraint succeeds does BESA publish
the resolved booleans, enable compiler languages implied by `toolchain-*`, and create any
compiler-dependent instrumentation policy.

After this phase boundary, model-declared dependencies and source/directory prefixes, plus any
backend-specific targets and tests, are processed against a frozen configuration. This prevents a dependency or subdirectory from implicitly changing the
meaning of configuration selection halfway through a configure run.

Project-wide packaging and instrumentation reporting need the final target/dependency graph. BESA
therefore schedules those operations with CMake's deferred-call mechanism and executes them after the
project tree has been processed.
