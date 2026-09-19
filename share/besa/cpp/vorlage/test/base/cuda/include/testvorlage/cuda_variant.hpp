// -------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------
#ifndef TESTBESA_PROJECT_UPPER_CUDA_VARIANT_HPP
#define TESTBESA_PROJECT_UPPER_CUDA_VARIANT_HPP

namespace testvorlage {

/// Documentation probe that is present only in the CUDA API variant.
[[nodiscard]] inline constexpr auto cuda_variant_only() noexcept -> int
{
  return 42;
}

} // namespace testvorlage

#endif // TESTBESA_PROJECT_UPPER_CUDA_VARIANT_HPP
