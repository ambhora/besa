// -------------------------------------------------------------------------------------------------
// SPDX-FileCopyrightText: 2026 BESA developers
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------
#ifndef BASIC_GREET_HPP
#define BASIC_GREET_HPP

#include <string>

namespace basic {

/** Returns a greeting for name. */
[[nodiscard]] std::string greet(std::string const& name);

} // namespace basic

#endif // BASIC_GREET_HPP
