// --------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 besa developers
// --------------------------------------------------------------------------------------------------
#ifndef BASIC_GREET_HPP
#define BASIC_GREET_HPP

#include <string>

namespace basic {

/** Returns a greeting for name. */
[[nodiscard]] std::string greet(std::string const& name);

} // namespace basic

#endif // BASIC_GREET_HPP
