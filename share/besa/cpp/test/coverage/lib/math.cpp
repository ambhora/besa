// -------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------

#include <math.hpp>

namespace A {
auto square(int x) -> int
{
  return x * x;
}

auto cube(int x) -> int
{
  return x * x * x;
}

auto quadratic(int x) -> int
{
  return x * x * x * x;
}
} // namespace A
