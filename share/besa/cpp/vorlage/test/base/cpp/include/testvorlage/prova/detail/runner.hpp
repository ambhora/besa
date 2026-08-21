// -------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------

#ifndef TESTVORLAGE_PROVA_DETAIL_RUNNER_HPP
#define TESTVORLAGE_PROVA_DETAIL_RUNNER_HPP

#include <string>
#include <testvorlage/prova/data.hpp>

namespace testvorlage::prova::detail {
auto runner(
  int argc,
  char** argv,
  testvorlage::prova::data::path& project_prefix,
  testvorlage::prova::data::path& group_prefix,
  std::string const& suffix) -> int;

} // namespace testvorlage::prova::detail

#endif // TESTVORLAGE_PROVA_DETAIL_RUNNER_HPP
