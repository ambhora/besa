# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Tests have their own first-class dependency graph.  libtestvorlage is intentionally not part of
# the installed product and may depend on libraries which the production library never sees.

add_library(libtestvorlage INTERFACE)
target_link_libraries(libtestvorlage INTERFACE vorlage::libvorlage)

add_library(vorlage.test.runtime INTERFACE)
target_link_libraries(vorlage.test.runtime INTERFACE libtestvorlage)

add_library(vorlage.test.unit INTERFACE)
target_link_libraries(vorlage.test.unit INTERFACE vorlage.test.runtime Catch2::Catch2WithMain)

# The starter project defines only `ci-commit`.  Runtime/compile discovery functions declare their
# supported modes themselves.  Smoke tests are registered manually, so gate their subdirectory with
# the public test-mode check helper to ensure that their targets are not even built in other modes.
besa_test_modes_check(
  OUTPUT_VARIABLE _enable_ci_commit_smoke
  MODES ci-commit
)
if(_enable_ci_commit_smoke)
  add_subdirectory(smoke)
endif()

add_subdirectory(unit)
add_subdirectory(compile)
