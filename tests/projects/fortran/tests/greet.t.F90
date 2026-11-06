! --------------------------------------------------------------------------------------------------
! SPDX-License-Identifier: Apache-2.0
! SPDX-FileCopyrightText: 2026 besa developers
! --------------------------------------------------------------------------------------------------
! A Fortran test using the library's public module.
program greet_test
  use greet, only: greeting
  implicit none
  if (greeting() /= "hello") error stop 1
end program greet_test
