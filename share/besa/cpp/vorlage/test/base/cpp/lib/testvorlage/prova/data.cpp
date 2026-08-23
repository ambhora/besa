// -------------------------------------------------------------------------------------------------
// SPDX-FileCopyrightText: 2026 BESA developers
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------

#include <testvorlage/prova/data.hpp>
#include <utility>

namespace testvorlage::prova::data {
path::path(std::string input, std::string output)
: input_(std::move(input)), output_(std::move(output))
{
}

auto path::input() const noexcept -> std::string const&
{
  return input_;
}

auto path::output() const noexcept -> std::string const&
{
  return output_;
}

auto path_from_prefix(path const& prefix, std::string const& suffix) -> path
{
  return {prefix.input() + std::string("/") + suffix, prefix.output() + std::string("/") + suffix};
}

} // namespace testvorlage::prova::data
