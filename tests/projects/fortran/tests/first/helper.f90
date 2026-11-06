! --------------------------------------------------------------------------------------------------
! SPDX-License-Identifier: Apache-2.0
! SPDX-FileCopyrightText: 2026 besa developers
! --------------------------------------------------------------------------------------------------
module helper
  implicit none
  private
  public :: expected
contains
  function expected() result(text)
    character(len=:), allocatable :: text
    text = "first"
  end function expected
end module helper
