// -------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------
#include <vorlage/version.hpp>
#include <vorlage/vorlage.hpp>

#include <iostream>

int main()
{
  std::cout << vorlage::hello() << " vorlage " << vorlage::version << '\n';
  return 0;
}
