// -------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------

auto main(int argc, char** /*argv*/) -> int
{
  int* array = new int[100]; // NOLINT
  for (int i = 0; i < 100; ++i) {
    array[i] = i; // NOLINT
  }
  array[argc] = 0;                // NOLINT
  int return_value = array[argc]; // NOLINT

  delete[] array;      // NOLINT
  return return_value; // NOLINT
}
