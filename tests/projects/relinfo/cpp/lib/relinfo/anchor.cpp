// -------------------------------------------------------------------------------------------------
// SPDX-FileCopyrightText: 2026 BESA developers
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------
#include <relinfo/version.hpp>

namespace relinfo {

int anchor()
{
  return static_cast<int>(meta::version().major);
}

} // namespace relinfo
