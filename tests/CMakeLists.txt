# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Every test configures, builds, and tests a small project under projects/ against a staged
# installation of BESA, so the tests exercise exactly what find_package(besa) delivers.
#
# The compiler under test is taken from the environment (CC/CXX) when the tests run, so the same
# build tree can be checked with several toolchains:
#
#   ctest --test-dir build                  # default compilers
#   CC=clang CXX=clang++ ctest --test-dir build

set(BESA_TEST_PREFIX "${PROJECT_BINARY_DIR}/tests/stage")
set(BESA_TEST_WORK "${PROJECT_BINARY_DIR}/tests/work")
set(BESA_TEST_PROJECTS "${CMAKE_CURRENT_SOURCE_DIR}/projects")
set(BESA_TEST_GENERATOR "${CMAKE_GENERATOR}" CACHE STRING
  "CMake generator used for the test projects"
)
set(BESA_TEST_CMAKE_ARGS "" CACHE STRING
  "Extra configure arguments passed to every test project"
)

add_test(
  NAME besa.stage
  COMMAND "${CMAKE_COMMAND}"
    "-DBINARY_DIR=${PROJECT_BINARY_DIR}"
    "-DPREFIX=${BESA_TEST_PREFIX}"
    "-DCMAKEDIR=${BESA_INSTALL_CMAKEDIR}"
    -P "${CMAKE_CURRENT_SOURCE_DIR}/stage.cmake"
)
set_tests_properties(besa.stage PROPERTIES FIXTURES_SETUP besa.stage LABELS "package")

# besa_project_test(
#   NAME     <test name>
#   PROJECT  <directory below projects/>
#   [EXPECT  PASS|CONFIGURE_FAIL|BUILD_FAIL|TEST_FAIL]
#   [MATCH   <regex the failing step must print>]
#   [CHECK   <script below projects/ run after configure>]
#   [CONSUMER <directory below projects/ built against the installed project>]
#   [ARGS    <configure arguments...>]
#   [LABELS  <labels...>]
# )
function(besa_project_test)
  cmake_parse_arguments(ARG "" "NAME;PROJECT;EXPECT;MATCH;CHECK;CONSUMER" "ARGS;LABELS" ${ARGN})
  if(ARG_UNPARSED_ARGUMENTS)
    message(FATAL_ERROR "besa_project_test: unknown arguments: ${ARG_UNPARSED_ARGUMENTS}")
  endif()
  foreach(_required NAME PROJECT)
    if(NOT ARG_${_required})
      message(FATAL_ERROR "besa_project_test: ${_required} is required")
    endif()
  endforeach()
  if(NOT ARG_EXPECT)
    set(ARG_EXPECT PASS)
  endif()

  set(_arguments ${BESA_TEST_CMAKE_ARGS} ${ARG_ARGS})
  string(REPLACE ";" "|" _arguments "${_arguments}")
  set(_command
    "${CMAKE_COMMAND}"
    "-DSOURCE=${BESA_TEST_PROJECTS}/${ARG_PROJECT}"
    "-DWORK=${BESA_TEST_WORK}/${ARG_NAME}"
    "-DPREFIX=${BESA_TEST_PREFIX}"
    "-DGENERATOR=${BESA_TEST_GENERATOR}"
    "-DEXPECT=${ARG_EXPECT}"
    "-DARGS=${_arguments}"
  )
  if(DEFINED ARG_MATCH)
    list(APPEND _command "-DMATCH=${ARG_MATCH}")
  endif()
  if(ARG_CHECK)
    list(APPEND _command "-DCHECK=${BESA_TEST_PROJECTS}/${ARG_CHECK}")
  endif()
  if(ARG_CONSUMER)
    list(APPEND _command -DINSTALL=ON "-DCONSUMER=${BESA_TEST_PROJECTS}/${ARG_CONSUMER}")
  endif()
  list(APPEND _command -P "${CMAKE_CURRENT_SOURCE_DIR}/driver.cmake")

  add_test(NAME "${ARG_NAME}" COMMAND ${_command})
  set_tests_properties("${ARG_NAME}" PROPERTIES FIXTURES_REQUIRED besa.stage)
  if(ARG_LABELS)
    set_tests_properties("${ARG_NAME}" PROPERTIES LABELS "${ARG_LABELS}")
  endif()
endfunction()

# --------------------------------------------------------------------------------------------------
# Package
# --------------------------------------------------------------------------------------------------
besa_project_test(NAME package.version.accepted PROJECT findpackage
  ARGS -DREQUESTED_VERSION=${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}
  LABELS package
)
besa_project_test(NAME package.version.rejected PROJECT findpackage
  ARGS -DREQUESTED_VERSION=99.0
  EXPECT CONFIGURE_FAIL MATCH "Could not find a configuration file.*compatible"
  LABELS package
)

# --------------------------------------------------------------------------------------------------
# Project layout, tests, installation, and consumption
# --------------------------------------------------------------------------------------------------
besa_project_test(NAME layout.cpp PROJECT basic CONSUMER basic-consumer
  CHECK basic/check-manifest.cmake
  LABELS core
)
besa_project_test(NAME layout.generated PROJECT generated CHECK generated/check-manifest.cmake LABELS core)
besa_project_test(NAME layout.compile-tests PROJECT compile LABELS core)
besa_project_test(NAME layout.freeze PROJECT basic
  ARGS -DFREEZE_VIOLATION=ON
  EXPECT CONFIGURE_FAIL MATCH "already been frozen"
  LABELS core
)

# --------------------------------------------------------------------------------------------------
# Features and Keyso feature spaces
# --------------------------------------------------------------------------------------------------
besa_project_test(NAME feature.default PROJECT features
  ARGS "-DEXPECTED_FEATURES=alpha"
  LABELS feature
)
besa_project_test(NAME feature.selection PROJECT features
  ARGS
    "-DPROJECT_FEATURES=beta$<SEMICOLON>mpi$<SEMICOLON>gpu"
    "-DEXPECTED_FEATURES=beta$<SEMICOLON>mpi$<SEMICOLON>gpu"
  LABELS feature
)
besa_project_test(NAME feature.mutually-exclusive PROJECT features
  ARGS "-DPROJECT_FEATURES=alpha$<SEMICOLON>beta"
  EXPECT CONFIGURE_FAIL MATCH "is not allowed by project feature space 'supported'"
  LABELS feature
)
besa_project_test(NAME feature.unknown PROJECT features
  ARGS -DPROJECT_FEATURES=gamma
  EXPECT CONFIGURE_FAIL MATCH "unknown feature 'gamma'"
  LABELS feature
)
besa_project_test(NAME feature.cpdocs-feature-sets PROJECT features
  ARGS -DWRITE_CPDOCS_FEATURE_SETS=ON
  CHECK features/check-feature-sets.cmake
  LABELS feature
)
besa_project_test(NAME feature.language-is-independent PROJECT languages
  ARGS -DSELECT_GPU_FROM_CPDOCS=ON
  CHECK languages/check-manifest.cmake
  LABELS feature
)

# --------------------------------------------------------------------------------------------------
# Test modes
# --------------------------------------------------------------------------------------------------
besa_project_test(NAME testmode.default PROJECT testmodes
  ARGS -DEXPECT_MERGE_TESTS=OFF
  LABELS testmode
)
besa_project_test(NAME testmode.override PROJECT testmodes
  ARGS -DTEST_MODES=ci-merge -DEXPECT_MERGE_TESTS=ON
  LABELS testmode
)
besa_project_test(NAME testmode.unknown PROJECT testmodes
  ARGS -DTEST_MODES=nightly
  EXPECT CONFIGURE_FAIL MATCH "unknown test mode 'nightly'"
  LABELS testmode
)

# --------------------------------------------------------------------------------------------------
# Versioning
# --------------------------------------------------------------------------------------------------
besa_project_test(NAME version.release PROJECT relinfo
  ARGS -DRELEASE_TYPE=release -DEXPECTED_SEMVER=1.2.3 -DEXPECTED_RELEASE=release
  LABELS version
)
besa_project_test(NAME version.rc PROJECT relinfo
  ARGS -DRELEASE_TYPE=rc -DRELEASE_REVISION=2 -DEXPECTED_SEMVER=1.2.3-rc.2
    -DEXPECTED_RELEASE=rc.2
  LABELS version
)
besa_project_test(NAME version.invalid PROJECT relinfo
  ARGS -DRELEASE_TYPE=final
  EXPECT CONFIGURE_FAIL MATCH "invalid RELEASE_TYPE 'final'"
  LABELS version
)

# --------------------------------------------------------------------------------------------------
# Warning policies
# --------------------------------------------------------------------------------------------------
besa_project_test(NAME warning.essential PROJECT warnings LABELS warning)
besa_project_test(NAME warning.error PROJECT warnings
  ARGS "-DPROJECT_WARNINGS=essential$<SEMICOLON>error"
  EXPECT BUILD_FAIL MATCH "unused"
  LABELS warning
)
besa_project_test(NAME warning.unknown PROJECT warnings
  ARGS -DPROJECT_WARNINGS=pedantic
  EXPECT CONFIGURE_FAIL MATCH "unknown warning policy 'pedantic'"
  LABELS warning
)

# --------------------------------------------------------------------------------------------------
# Devtools
# --------------------------------------------------------------------------------------------------
besa_project_test(NAME devtool.unknown PROJECT warnings
  ARGS -DPROJECT_DEVTOOLS=valgrind
  EXPECT CONFIGURE_FAIL MATCH "unknown devtool 'valgrind'"
  LABELS devtool
)
besa_project_test(NAME devtool.surrogate PROJECT surrogate
  ARGS -DPROJECT_DEVTOOLS=surrogate
  LABELS devtool
)
besa_project_test(NAME devtool.surrogate.broken PROJECT surrogate
  ARGS -DPROJECT_DEVTOOLS=surrogate -DSURROGATE_BROKEN=ON
  EXPECT TEST_FAIL MATCH "surrogate\\.liboops\\.t"
  LABELS devtool
)
foreach(_sanitizer IN ITEMS asan ubsan)
  besa_project_test(NAME devtool.${_sanitizer} PROJECT sanitizers
    ARGS -DPROJECT_DEVTOOLS=${_sanitizer} -DSANITIZER=${_sanitizer}
    LABELS devtool
  )
endforeach()

find_program(BESA_TEST_CLANG_FORMAT clang-format)
if(BESA_TEST_CLANG_FORMAT)
  besa_project_test(NAME devtool.format PROJECT format
    ARGS -DPROJECT_DEVTOOLS=format
    LABELS devtool
  )
  besa_project_test(NAME devtool.format.broken PROJECT format-broken
    ARGS -DPROJECT_DEVTOOLS=format
    EXPECT TEST_FAIL MATCH "clang-format failed"
    LABELS devtool
  )
endif()

find_program(BESA_TEST_RUN_CLANG_TIDY run-clang-tidy)
find_program(BESA_TEST_CLANG_TIDY clang-tidy)
if(BESA_TEST_RUN_CLANG_TIDY AND BESA_TEST_CLANG_TIDY)
  besa_project_test(NAME devtool.linting PROJECT format
    ARGS -DPROJECT_DEVTOOLS=linting -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
    LABELS devtool
  )
endif()

find_program(BESA_TEST_GCOVR gcovr)
find_program(BESA_TEST_LLVM_COV llvm-cov)
find_program(BESA_TEST_LLVM_PROFDATA llvm-profdata)
if(BESA_TEST_GCOVR OR (BESA_TEST_LLVM_COV AND BESA_TEST_LLVM_PROFDATA))
  besa_project_test(NAME devtool.coverage PROJECT coverage
    ARGS -DPROJECT_DEVTOOLS=coverage
    CHECK coverage/check-tests.cmake
    LABELS devtool
  )
endif()
