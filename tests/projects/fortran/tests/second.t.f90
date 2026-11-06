! --------------------------------------------------------------------------------------------------
! SPDX-License-Identifier: Apache-2.0
! SPDX-FileCopyrightText: 2026 besa developers
! --------------------------------------------------------------------------------------------------
! Uses the helper module of its companion directory, second/. The other test's companion defines a
! module with the same name, so each test needs its own module directory.
program second_test
  use helper, only: expected
  implicit none
  if (expected() /= "second") error stop 1
end program second_test
