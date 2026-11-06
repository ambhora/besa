! --------------------------------------------------------------------------------------------------
! SPDX-License-Identifier: Apache-2.0
! SPDX-FileCopyrightText: 2026 besa developers
! --------------------------------------------------------------------------------------------------
! Uses the helper module of its companion directory, first/. The other test's companion defines a
! module with the same name, so each test needs its own module directory.
program first_test
  use helper, only: expected
  implicit none
  if (expected() /= "first") error stop 1
end program first_test
