// --------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 besa developers
// --------------------------------------------------------------------------------------------------
#include <basic/greet.hpp>
#include <basic/version.hpp>

int main()
{
  auto const version = basic::meta::version();
  bool const ok = version.major == 1 && version.minor == 2 && version.patch == 3;
  return ok && basic::greet("consumer") == "hello consumer from 1.2.3" ? 0 : 1;
}
