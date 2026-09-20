// -------------------------------------------------------------------------------------------------
// SPDX-FileCopyrightText: 2026 BESA developers
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------

#include <catch2/catch_session.hpp>
#include <testvorlage/prova/cmdline.hpp>
#include <testvorlage/prova/data.hpp>
#include <testvorlage/prova/detail/runner.hpp>
#include <vector>

namespace testvorlage::prova::detail {
auto runner(
  int argc,
  char** argv,
  testvorlage::prova::data::path& project_prefix,
  testvorlage::prova::data::path& group_prefix,
  std::string const& suffix) -> int
{
  auto result = testvorlage::prova::cmdline::parse(argc, argv);

  project_prefix = result.path();
  group_prefix = testvorlage::prova::data::path_from_prefix(project_prefix, suffix);

  std::vector<char const*> catch_arguments;
  catch_arguments.reserve(result.residual().size());
  for (auto const& argument : result.residual()) {
    catch_arguments.push_back(argument.c_str());
  }

  Catch::Session session;
  int const return_code
    = session.applyCommandLine(static_cast<int>(catch_arguments.size()), catch_arguments.data());
  if (return_code != 0) {
    return return_code;
  }

  return session.run();
}

} // namespace testvorlage::prova::detail
