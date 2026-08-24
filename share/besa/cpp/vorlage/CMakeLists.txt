# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# This file is intentionally a description of project intent rather than an implementation of build
# mechanics.  BESA owns feature resolution, compiler-language activation, dependency bookkeeping,
# target instrumentation, testing conventions, package export, and version generation.  The project
# remains responsible for declaring its topology and domain-specific feature constraints.

cmake_minimum_required(VERSION 3.26.1)

# besa.toml is the authoritative project declaration.  The tiny bootstrap reader is usable before
# project() so even project identity is not duplicated in CMake.
include("${CMAKE_CURRENT_SOURCE_DIR}/cmake/besa/model.cmake")
besa_model_bootstrap(FILE "${CMAKE_CURRENT_SOURCE_DIR}/besa.toml")

# No compiler language is enabled here.  Enabled `toolchain-*` features are resolved first and
# besa_configure_complete() enables the corresponding CMake languages afterwards.
project(
  "${BESA_MODEL_PROJECT_NAME}"
  VERSION "${BESA_MODEL_PROJECT_VERSION}"
  LANGUAGES NONE
)

# Always emit compile_commands.json for editor, analysis, and developer tooling.
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Configure the Doxygen parser from this exact build tree. This is intentionally done even when
# user-docs is disabled: sphinx-multiversion configures historical refs with ~user-docs and still
# needs a checkout-specific Doxyfile pointing at that ref's compile_commands.json.
file(MAKE_DIRECTORY "${PROJECT_BINARY_DIR}/api-docs")
configure_file(
  "${PROJECT_SOURCE_DIR}/api-docs/Doxyfile.in"
  "${PROJECT_BINARY_DIR}/api-docs/Doxyfile"
  @ONLY
)

# The BESA CMake implementation is vendored into the repository by `besa cpp generate` and may later
# be replaced in-place with `besa cpp update`.  The project therefore has no dependency on a global
# BESA installation when it is configured or built.
list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake/besa")
find_package(besa CONFIG REQUIRED)

# --------------------------------------------------------------------------------------------------
# BUILD OPTIONS
# --------------------------------------------------------------------------------------------------

# PROJECT_FEATURES (Variable)
# Explicit overrides to the default feature set.  A positive name enables a feature and `~name`
# disables a default feature.  A feature may appear at most once; `foo;~foo` is an error rather than
# an ordering rule.
set(PROJECT_FEATURES "" CACHE STRING "Explicit project feature overrides")

# PROJECT_DEVTOOLS (Variable)
# List of instrumentation/developer tools to be enabled for the build.  `none` is mutually exclusive
# with every other value.  These settings alter target policy or register QA tests, but do not alter
# the structural feature graph.
set(PROJECT_DEVTOOLS "none" CACHE STRING "List of Devtools")

# PROJECT_WARNINGS (Variable)
# BESA owns the set of supported warning policies; the project only selects which policies are active.
# Policies are composable, so `essential;error` enables the normal warning set and promotes warnings
# to errors.  `none` explicitly disables all BESA warning policy and must appear alone.
set(PROJECT_WARNINGS "essential" CACHE STRING "BESA warning policies enabled for this build")

# TEST_MODES (Variable)
# Explicit overrides to the project-defined default test modes.  Test modes use the same override
# semantics as features: `mode` enables and `~mode` disables a default.  Test-mode names have no
# built-in meaning in BESA; projects define the workflows they need.
set(TEST_MODES "" CACHE STRING "Explicit project test-mode overrides")

# BUILD_TESTING (Option)
# Tests are disabled by default for package consumers.  Define this before including CTest because
# CTest otherwise creates BUILD_TESTING with an ON default.
option(BUILD_TESTING "Build the test suite" OFF)
include(CTest)

# --------------------------------------------------------------------------------------------------
# RELEASE OPTIONS (Intended for Release Management)
# --------------------------------------------------------------------------------------------------

# RELEASE_TYPE (Variable)
# The variable selects the type of release or prerelease version to be used.
# The following release types are supported:
# a. `dev`     : The version is not a release. Use the git-based version instead.
# b. `release` : The version is a release.
# c. `alpha`   : The version is an alpha release.
# d. `beta`    : The version is a beta release.
# e. `rc`      : The version is an RC release.
set(RELEASE_TYPE "dev" CACHE STRING "Type of Release")

# RELEASE_REVISION (Variable)
# The variable selects the revision of the prerelease under consideration.  For example, for an
# `rc.1` prerelease, RELEASE_REVISION is `1`.
set(RELEASE_REVISION "1" CACHE STRING "Revision of Release")

# --------------------------------------------------------------------------------------------------
# PACKAGING OPTIONS
#
# These options are intended primarily for downstream package maintainers and other builders who
# redistribute the software. They are deliberately independent of the upstream release metadata so
# two artifacts built from the same source version can still be distinguished by builder and
# downstream packaging revision.
# --------------------------------------------------------------------------------------------------

# PKGBUILDER_ID (Variable)
# Identity of the downstream builder or package maintainer that produced the artifact. The default
# `vanilla` value identifies a build without downstream packaging identity.
set(PKGBUILDER_ID "vanilla" CACHE STRING "Package builder identifier")

# PKGBUILDER_REVISION (Variable)
# Downstream packaging revision. This is for respins or packaging-only changes and does not alter
# PROJECT_VERSION, RELEASE_TYPE, RELEASE_REVISION, or PROJECT_SEMVER.
set(PKGBUILDER_REVISION "1" CACHE STRING "Package builder revision")

# --------------------------------------------------------------------------------------------------
# DECLARATIVE PROJECT MODEL
# --------------------------------------------------------------------------------------------------

# CMake supplies the selected build configuration (PROJECT_FEATURES, BUILD_TESTING, devtools,
# warnings, test modes, and the toolchain).  besa.toml declares what the project can contain.
# BESA validates/resolves that model and realizes the selected configuration through this backend.
besa_model_realize(FILE "${PROJECT_SOURCE_DIR}/besa.toml")
