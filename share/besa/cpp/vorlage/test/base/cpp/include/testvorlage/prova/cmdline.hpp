// -------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------

#ifndef TESTVORLAGE_PROVA_CMDLINE_HPP
#define TESTVORLAGE_PROVA_CMDLINE_HPP

#include <string>
#include <testvorlage/prova/data.hpp>
#include <utility>
#include <vector>

namespace testvorlage::prova::cmdline {
class result {
public:
  result() = default;
  result(testvorlage::prova::data::path path, std::vector<std::string> cmdline)
  : path_(std::move(path)), cmdline_(std::move(cmdline))
  {
  }

public:
  auto path() const noexcept -> testvorlage::prova::data::path const& { return path_; }
  auto residual() const noexcept -> std::vector<std::string> const& { return cmdline_; }

private:
  testvorlage::prova::data::path path_;
  std::vector<std::string> cmdline_;
};

/**
 * Parse the Prova command line into project paths and residual Catch2 arguments.
 *
 * For project-level developer documentation, see @projectdocs. For the testing conventions used by
 * this support library, see @projectdocs{reference/testing,the testing reference}.
 */
auto parse(int argc, char** argv) -> result;
} // namespace testvorlage::prova::cmdline

#endif // TESTVORLAGE_PROVA_CMDLINE_HPP
