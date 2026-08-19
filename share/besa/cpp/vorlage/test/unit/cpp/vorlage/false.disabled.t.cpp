#include <catch2/catch_test_macros.hpp>
TEST_CASE("disabled test convention") { FAIL("disabled tests must not execute"); }
