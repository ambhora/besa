// -------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------
#include <catch2/catch_test_macros.hpp>
#include <vorlage/vorlage.hpp>

TEST_CASE("hello world API", "[vorlage]")
{
  REQUIRE(vorlage::hello() == "Hello, world!");
}
