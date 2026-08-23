# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# This file is intentionally a description of project intent rather than an implementation of build
# mechanics.  BESA owns feature resolution, compiler-language activation, dependency bookkeeping,
# target instrumentation, testing conventions, package export, and version generation.  The project
# remains responsible for declaring its topology and domain-specific feature constraints.

cmake_minimum_required(VERSION 3.26.1)

# No compiler language is enabled here.  Enabled `toolchain-*` features are resolved first and
# besa_configure_complete() enables the corresponding CMake languages afterwards.
project(vorlage VERSION 0.1.0 LANGUAGES NONE)

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
# FEATURE / TEST-MODE DECLARATION AND CONFIGURATION
# --------------------------------------------------------------------------------------------------

# `build-source` is a normal feature and is enabled by default.  `toolchain-*` is a reserved feature
# prefix: when such a feature survives resolution BESA enables the corresponding CMake language
# before any dependency or source directory is processed.
besa_features_add(
  FEATURES
    build-source
    toolchain-cpp
    user-docs
    project-kosha25
    showcase-hello
)

besa_features_default(
  FEATURES
    build-source
    toolchain-cpp
)

# Test modes are project-defined, unlike warning policies and devtools which are capabilities owned
# by BESA.  The starter template has one mode only; projects can add their own modes later without
# requiring any BESA change.
besa_test_modes_add(
  MODES
    ci-commit
)

besa_test_modes_default(
  MODES
    ci-commit
)

# Project-specific feature/devtool/test-mode constraints, if any, are registered before this call.
# This is the explicit phase boundary: after it, configuration sets are frozen and dependencies,
# directories, targets, and tests may be declared.
besa_configure_complete()

# --------------------------------------------------------------------------------------------------
# DEPENDENCIES
# --------------------------------------------------------------------------------------------------

# Development dependencies never appear in the generated vorlageConfig.cmake.  Normal dependencies
# declared with KIND NORMAL do; build-only dependencies do not.
if(BUILD_TESTING)
  besa_dependency_add(
    NAME Catch2
    VERSION 3
    KIND DEV
    PROVIDER CMAKE
  )
  besa_dependency_add(
    NAME Threads
    KIND DEV
    PROVIDER CMAKE
  )
endif()

# Doxygen is discovered as a CMake development dependency. ProperDocs, Sphinx, Breathe, and
# sphinx-multiversion are documentation executables/modules validated by the documentation helpers
# and are provided by the development environment rather than exported as package dependencies.
besa_dependency_add(
  NAME Doxygen
  KIND DEV
  PROVIDER CMAKE
  WHEN ALL_OF user-docs
)

# --------------------------------------------------------------------------------------------------
# PROJECT STRUCTURE
# --------------------------------------------------------------------------------------------------

besa_add_directory(
  NAME src
  WHEN ALL_OF build-source
)

# Regex selectors allow a parent directory to participate whenever at least one feature in its
# namespace is enabled.  Individual children make the final, explicit feature decision themselves.
besa_add_directory(
  NAME project
  WHEN REGEX "^project-"
)

besa_add_directory(
  NAME showcases
  WHEN REGEX "^showcase-"
)

besa_add_directory(
  NAME docs
  WHEN ALL_OF user-docs
)

if(BUILD_TESTING)
  add_subdirectory(test)
endif()
