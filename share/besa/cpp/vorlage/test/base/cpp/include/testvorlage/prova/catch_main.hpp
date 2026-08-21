// -------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------

#ifndef TESTVORLAGE_PROVA_CATCH_MAIN_HPP
#define TESTVORLAGE_PROVA_CATCH_MAIN_HPP

#include <string>
#include <testvorlage/prova/data.hpp>
#include <testvorlage/prova/detail/runner.hpp>

// Define the custom Catch2 entry point for a test group. Targets using this macro must link the
// project's test runtime, which links Catch2::Catch2 without Catch2's supplied main.
// NOLINTNEXTLINE(cppcoreguidelines-macro-usage)
#define TESTVORLAGE_PROVA_CATCH_MAIN(suffix)                                                      \
  /* NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables) */                         \
  testvorlage::prova::data::path project_prefix = testvorlage::prova::data::path();               \
  /* NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables) */                         \
  testvorlage::prova::data::path group_prefix = testvorlage::prova::data::path();                 \
                                                                                                  \
  auto main(int argc, char* argv[]) -> int                                                        \
  {                                                                                               \
    return testvorlage::prova::detail::runner(                                                    \
      argc, argv, project_prefix, group_prefix, std::string(suffix));                             \
  }

// Declare the paths populated by TESTVORLAGE_PROVA_CATCH_MAIN for another translation unit in the
// same test.
// NOLINTNEXTLINE(cppcoreguidelines-macro-usage)
#define TESTVORLAGE_PROVA_CATCH_GROUP()                                                           \
  /* NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables) */                         \
  extern testvorlage::prova::data::path project_prefix;                                           \
  /* NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables) */                         \
  extern testvorlage::prova::data::path group_prefix;

#endif // TESTVORLAGE_PROVA_CATCH_MAIN_HPP
