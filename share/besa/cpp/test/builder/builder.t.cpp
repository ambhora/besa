// -------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------

#include <cstdlib>
#include <simple.hpp>

auto main() -> int
{
  if (f(2, 2.0) != 4.0) {
    return EXIT_FAILURE;
  }

  return EXIT_SUCCESS;
}
