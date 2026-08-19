// -------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------

// NOLINTNEXTLINE
#include <stdlib.h>

// NOLINTNEXTLINE
void* p;

// NOLINTNEXTLINE
int main()
{
  // NOLINTNEXTLINE
  p = malloc(7);
  // NOLINTNEXTLINE
  p = 0; // The memory is leaked here.
  return 0;
}
