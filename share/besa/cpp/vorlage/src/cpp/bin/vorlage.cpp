// -------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------
#include <vorlage/vorlage.hpp>

#include <iostream>

int main()
{
  std::cout << "vorlage " << vorlage::meta::to_string(vorlage::meta::version());
  std::cout << " (" << vorlage::meta::to_string(vorlage::meta::release()) << ")\n";
  return 0;
}
