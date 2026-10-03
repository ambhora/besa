# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------
import pathlib as _pathlib

import pytest as _pytest

import besa_dev.ci as _ci
import besa_dev.compilers as _compilers

CONFIG = _pathlib.Path(__file__).parents[1] / "etc" / "compilers.json"
ROOT = CONFIG.parents[2]


def test_matrix_lists_every_compiler_once() -> None:
    config = _compilers.load(CONFIG)
    entries = _ci.matrix(config)["include"]
    assert [entry["id"] for entry in entries] == [
        _ci.identifier(compiler) for compiler in config.compilers
    ]
    assert all(
        set(entry) == {"id", "name", "experimental"} for entry in entries
    )


def test_environment_expands_family_templates() -> None:
    config = _compilers.load(CONFIG)
    compiler = _compilers.Compiler("clang", 23, False)
    environment = _ci.environment(config, compiler)
    assert environment["BESA_CI_ID"] == "clang-23"
    assert environment["BESA_CI_PATH"] == "/usr/lib/llvm-23/bin"
    assert "llvm.sh 23 all" in environment["BESA_CI_SETUP"]
    assert "{version}" not in "".join(environment.values())


def test_container_command_mounts_root_and_runs_script() -> None:
    config = _compilers.load(CONFIG)
    compiler = _ci.find(config, "gcc-16")
    command = _ci.container_command(config, compiler, ROOT, "podman")
    assert command[:3] == ["podman", "run", "--rm"]
    assert f"{ROOT.resolve()}:/src" in command
    assert command[-3:] == ["gcc:16", "bash", _ci.RUN_SCRIPT]
    assert (ROOT / _ci.RUN_SCRIPT).is_file()


def test_find_reports_known_compilers() -> None:
    config = _compilers.load(CONFIG)
    with _pytest.raises(_ci.UnknownCompilerError, match="gcc-16"):
        _ci.find(config, "gcc-1")
