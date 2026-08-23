# SPDX-License-Identifier: Apache-2.0
from spack_repo.builtin.packages.doxygen.package import Doxygen as BuiltinDoxygen

from spack.package import *


class Doxygen(BuiltinDoxygen):
    """Builtin Doxygen with optional libclang-assisted parsing."""

    variant(
        "libclang",
        default=False,
        description="Enable Doxygen CLANG_ASSISTED_PARSING support",
    )

    depends_on("llvm+clang", when="+libclang")

    def cmake_args(self):
        args = super().cmake_args()
        args.append(self.define_from_variant("use_libclang", "libclang"))
        return args
