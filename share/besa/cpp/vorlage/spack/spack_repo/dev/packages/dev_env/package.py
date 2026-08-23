# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
from spack_repo.builtin.build_systems.bundle import BundlePackage

from spack.package import *


class DevEnv(BundlePackage):
    """Development environment for this repository."""

    # Bump this version when the bundle dependency graph changes so existing
    # Spack environments can be explicitly reconcretized against the new graph.
    version("1.2")

    variant("docs", default=False, description="Documentation toolchain")
    variant("tests", default=True, description="C++ test dependencies")
    variant("coverage", default=False, description="Coverage reporting tools")

    depends_on("cmake")
    depends_on("ninja")
    depends_on("git")
    depends_on("gcc")
    depends_on("llvm")

    depends_on("catch2", when="+tests")
    depends_on("lcov", when="+coverage")
    depends_on("py-gcovr", when="+coverage")

    depends_on("doxygen+libclang", when="+docs")
    depends_on("graphviz", when="+docs")
    depends_on("py-sphinx@:8", when="+docs")
    depends_on("py-breathe", when="+docs")
    depends_on("py-exhale", when="+docs")
    depends_on("py-pydata-sphinx-theme", when="+docs")
    depends_on("py-sphinx-multiversion", when="+docs")
    depends_on("properdocs", when="+docs")
