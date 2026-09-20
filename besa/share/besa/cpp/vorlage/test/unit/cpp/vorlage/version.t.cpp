// -------------------------------------------------------------------------------------------------
// SPDX-FileCopyrightText: 2026 BESA developers
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------
#include <catch2/catch_test_macros.hpp>
#include <vorlage/vorlage.hpp>

TEST_CASE("version metadata mirrors the CMake project version", "[vorlage][meta]")
{
  auto constexpr version = vorlage::meta::version();
  auto constexpr release = vorlage::meta::release();
  auto constexpr build = vorlage::meta::build();

  static_assert(version.major == 0);
  static_assert(version.minor == 1);
  static_assert(version.patch == 0);
  static_assert(version.tweak == 0);
  static_assert(vorlage::meta::to_string(version) == "0.1.0");

  static_assert(release.type == vorlage::meta::release_type::development);
  static_assert(release.revision == 1);
  static_assert(vorlage::meta::to_string(release.type) == "dev");
  static_assert(vorlage::meta::to_string(release) == "dev");

  static_assert(!build.compiler.empty());
  static_assert(!build.compiler_version.empty());
  static_assert(!build.system.empty());
  static_assert(!build.processor.empty());
  static_assert(!build.build_type.empty());
  static_assert(!vorlage::meta::to_string(build).empty());
}
