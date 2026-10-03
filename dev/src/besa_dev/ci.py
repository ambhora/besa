# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------
"""Turn the compiler configuration into CI jobs and container commands.

The GitHub workflow asks for the matrix at run time, and every matrix job runs
the same container command a developer runs locally with ``besa-dev run``.
"""

import pathlib as _pathlib
import shlex as _shlex
import typing as _typing

import besa_dev.compilers as _compilers

RUN_SCRIPT = "dev/ci/run-tests.sh"
CONTAINER_SOURCE = "/src"


class UnknownCompilerError(Exception):
    """No configured compiler has the requested identifier."""


def identifier(compiler: _compilers.Compiler) -> str:
    """Stable identifier of a compiler, such as ``gcc-16``."""
    return f"{compiler.family}-{compiler.version}"


def find(config: _compilers.Config, name: str) -> _compilers.Compiler:
    """Return the compiler with identifier name."""
    for compiler in config.compilers:
        if identifier(compiler) == name:
            return compiler
    known = ", ".join(identifier(compiler) for compiler in config.compilers)
    raise UnknownCompilerError(f"unknown compiler '{name}'; known: {known}")


def matrix(config: _compilers.Config) -> dict[str, _typing.Any]:
    """The GitHub Actions matrix, one entry per configured compiler."""
    return {
        "include": [
            {
                "id": identifier(compiler),
                "name": f"{compiler.family} {compiler.version}",
                "experimental": compiler.experimental,
            }
            for compiler in config.compilers
        ]
    }


def environment(
    config: _compilers.Config, compiler: _compilers.Compiler
) -> dict[str, str]:
    """Environment passed to the run script inside the container."""
    family = _compilers.family(config, compiler.family)
    version = compiler.version
    setup = " && ".join(
        _compilers.expand(command, version) for command in family.setup
    )
    return {
        "BESA_CI_ID": identifier(compiler),
        "BESA_CI_SETUP": setup,
        "BESA_CI_PATH": _compilers.expand(family.path, version),
        "CC": _compilers.expand(family.cc, version),
        "CXX": _compilers.expand(family.cxx, version),
        "DEBIAN_FRONTEND": "noninteractive",
    }


def image(config: _compilers.Config, compiler: _compilers.Compiler) -> str:
    """Container image providing the compiler."""
    family = _compilers.family(config, compiler.family)
    return _compilers.expand(family.image, compiler.version)


def container_command(
    config: _compilers.Config,
    compiler: _compilers.Compiler,
    root: _pathlib.Path,
    engine: str,
) -> list[str]:
    """Command running the test suite for compiler in a fresh container."""
    command = [
        engine,
        "run",
        "--rm",
        "--volume",
        f"{root.resolve()}:{CONTAINER_SOURCE}",
        "--workdir",
        CONTAINER_SOURCE,
    ]
    for key, value in environment(config, compiler).items():
        command.extend(["--env", f"{key}={value}"])
    command.extend([image(config, compiler), "bash", RUN_SCRIPT])
    return command


def render(command: list[str]) -> str:
    """Shell-quoted form of a command, for display."""
    return _shlex.join(command)
