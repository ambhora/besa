// -------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------

// NOLINTNEXTLINE
int main([[maybe_unused]] int argc, [[maybe_unused]] char** argv)
{
  // NOLINTNEXTLINE
  [[maybe_unused]] int k = 0x7fffffff;
  // NOLINTNEXTLINE
  k += argc;
  return 0;
}
