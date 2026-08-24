// -------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------
#ifndef TESTBESA_PROJECT_UPPER_CUDA_PROFILE_HPP
#define TESTBESA_PROJECT_UPPER_CUDA_PROFILE_HPP

namespace testvorlage {

/// Documentation probe that is present only in the CUDA API profile.
[[nodiscard]] inline constexpr auto cuda_profile_only() noexcept -> int
{
  return 42;
}

} // namespace testvorlage

#endif // TESTBESA_PROJECT_UPPER_CUDA_PROFILE_HPP
