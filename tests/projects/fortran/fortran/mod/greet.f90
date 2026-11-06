! --------------------------------------------------------------------------------------------------
! SPDX-License-Identifier: Apache-2.0
! SPDX-FileCopyrightText: 2026 besa developers
! --------------------------------------------------------------------------------------------------
! Public module of the library: consumers 'use greet'.
module greet
  use greet_text, only: greeting_text
  implicit none
  private
  public :: greeting
contains
  function greeting() result(text)
    character(len=:), allocatable :: text
    text = greeting_text()
  end function greeting
end module greet
