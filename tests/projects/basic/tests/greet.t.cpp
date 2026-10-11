// --------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 besa developers
// --------------------------------------------------------------------------------------------------
#include <basic/greet.hpp>

#include <string>

std::string report(std::string const& value);

int main()
{
  return report(basic::greet("test")) == "[hello test from 1.2.3]" ? 0 : 1;
}
