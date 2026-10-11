// --------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 besa developers
// --------------------------------------------------------------------------------------------------
int main(int argc, char**)
{
  int volatile shift = 31 + argc;
  int volatile value = 1 << shift;
  return value == 0 ? 0 : 0;
}
