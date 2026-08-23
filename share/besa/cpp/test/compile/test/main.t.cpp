// -------------------------------------------------------------------------------------------------
// SPDX-FileCopyrightText: 2026 BESA developers
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------

#include <iostream>

int satellite_function();

int main()
{
  std::cout << "Hello, World!" << std::endl;
  if (satellite_function() != 42) {
    std::cerr << "Satellite function failed!" << std::endl;
    return EXIT_FAILURE;
  }
  return EXIT_SUCCESS;
}
