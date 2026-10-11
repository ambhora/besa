// --------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 besa developers
// --------------------------------------------------------------------------------------------------
#include <cstdlib>

int main(int argc, char**)
{
  auto* values = static_cast<int volatile*>(std::malloc(4 * sizeof(int)));
  values[argc + 3] = 1;
  std::free(const_cast<int*>(values));
  return 0;
}
