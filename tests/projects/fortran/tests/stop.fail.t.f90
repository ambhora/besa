! --------------------------------------------------------------------------------------------------
! SPDX-License-Identifier: Apache-2.0
! SPDX-FileCopyrightText: 2026 besa developers
! --------------------------------------------------------------------------------------------------
! Expected to fail: the .fail. suffix applies to Fortran tests too.
program stop_test
  implicit none
  error stop 1
end program stop_test
