// -------------------------------------------------------------------------------------------------
// SPDX-FileCopyrightText: 2026 BESA developers
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------
#include <relinfo/version.hpp>

#include <string_view>

int main()
{
  using namespace relinfo::meta;
  static_assert(version().major == 1 && version().minor == 2 && version().patch == 3);
  static_assert(to_string(semantic_version{}) == "1.2.3");
  return to_string(release()) == std::string_view(EXPECTED_RELEASE) ? 0 : 1;
}
