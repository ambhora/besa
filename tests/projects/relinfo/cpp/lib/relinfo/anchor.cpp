// --------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 besa developers
// --------------------------------------------------------------------------------------------------
#include <relinfo/version.hpp>

namespace relinfo {

int anchor()
{
  return static_cast<int>(meta::version().major);
}

} // namespace relinfo
