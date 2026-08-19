// -------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------

#include <iostream>
#include <math.hpp>

auto main() -> int
{
  auto x = 2;

  auto a = A::cube(x);
  std::cout << a << std::endl;

  if (a != 8) {
    return EXIT_FAILURE;
  }

  return EXIT_SUCCESS;
}
