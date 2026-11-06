! --------------------------------------------------------------------------------------------------
! SPDX-License-Identifier: Apache-2.0
! SPDX-FileCopyrightText: 2026 besa developers
! --------------------------------------------------------------------------------------------------
program consumer
  use greet, only: greeting
  implicit none
  if (greeting() /= "hello") error stop 1
end program consumer
