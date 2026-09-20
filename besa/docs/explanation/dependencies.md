<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Dependency model

BESA separates **why** a dependency exists from **how** CMake discovers it.

`KIND` is one of `NORMAL`, `BUILD`, or `DEV`. Normal dependencies belong to the product and are
written into generated consumer package metadata. Build dependencies are needed to construct the
software but not to consume it. Dev dependencies belong to testing, documentation, analysis, or
other development workflows and are never propagated to consumers.

`PROVIDER` currently distinguishes `CMAKE` from `PKGCONFIG`. The CMake provider deliberately relies on
`find_package()` rather than requiring a particular metadata format. Consequently a dependency can
move from a traditional CMake package config toward CPS when the active CMake/dependency supports it
without changing the BESA project declaration.

This information is intentionally richer than a raw `find_package()` call because it is also the
foundation for a future package/build model in which normal, build, and dev dependency graphs can be
handled differently.
