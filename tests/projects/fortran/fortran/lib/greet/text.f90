! --------------------------------------------------------------------------------------------------
! SPDX-License-Identifier: Apache-2.0
! SPDX-FileCopyrightText: 2026 besa developers
! --------------------------------------------------------------------------------------------------
! Private module, compiled into the library before the public module that uses it.
module greet_text
  implicit none
  private
  public :: greeting_text
contains
  function greeting_text() result(text)
    character(len=:), allocatable :: text
    text = "hello"
  end function greeting_text
end module greet_text
