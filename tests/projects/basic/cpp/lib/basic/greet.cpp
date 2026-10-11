// --------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 besa developers
// --------------------------------------------------------------------------------------------------
#include <basic/greet.hpp>
#include <basic/version.hpp>

#include <string>

namespace basic {

std::string greet(std::string const& name)
{
  return "hello " + name + " from " + std::string(meta::to_string(meta::version()));
}

} // namespace basic
