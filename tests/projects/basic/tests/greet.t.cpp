// -------------------------------------------------------------------------------------------------
// SPDX-FileCopyrightText: 2026 BESA developers
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------
#include <basic/greet.hpp>

#include <string>

std::string report(std::string const& value);

int main()
{
  return report(basic::greet("test")) == "[hello test from 1.2.3]" ? 0 : 1;
}
