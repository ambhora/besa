// -------------------------------------------------------------------------------------------------
// SPDX-FileCopyrightText: 2026 BESA developers
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------
#include <cstdlib>

int main(int argc, char**)
{
  auto* values = static_cast<int volatile*>(std::malloc(4 * sizeof(int)));
  values[argc + 3] = 1;
  std::free(const_cast<int*>(values));
  return 0;
}
