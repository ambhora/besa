// -------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------

#ifndef TESTBESA_PROJECT_UPPER_PROVA_DATA_HPP
#define TESTBESA_PROJECT_UPPER_PROVA_DATA_HPP

#include <string>

namespace testvorlage::prova::data {
class path {
public:
  path() = default;
  path(std::string input, std::string output);

public:
  auto input() const noexcept -> std::string const&;
  auto output() const noexcept -> std::string const&;

private:
  std::string input_;
  std::string output_;
};

auto path_from_prefix(path const& prefix, std::string const& suffix) -> path;
} // namespace testvorlage::prova::data

#endif // TESTBESA_PROJECT_UPPER_PROVA_DATA_HPP
