// -------------------------------------------------------------------------------------------------
// SPDX-FileCopyrightText: 2026 BESA developers
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------

auto main(int argc, char** /*argv*/) -> int
{
  int* array = new int[100]; // NOLINT
  delete[] array;            // NOLINT
  return array[argc];        // NOLINT
}
