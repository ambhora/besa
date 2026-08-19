from __future__ import annotations

from pathlib import Path

import pytest

import besa.cli as cli
from besa.cli import cpp_generate, cpp_update, main, python_generate


def test_share_directory_prefers_source_tree_over_installed_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "source"
    source_package = source_root / "src" / "besa"
    source_share = source_root / "share" / "besa"
    installed_prefix = tmp_path / "venv"
    installed_share = installed_prefix / "share" / "besa"

    source_package.mkdir(parents=True)
    source_share.mkdir(parents=True)
    installed_share.mkdir(parents=True)

    monkeypatch.delenv("BESA_SHARE_DIR", raising=False)
    monkeypatch.setattr(cli, "__file__", str(source_package / "cli.py"))
    monkeypatch.setattr(cli.sys, "prefix", str(installed_prefix))

    assert cli.share_directory() == source_share


def test_cpp_generate_vendors_cmake(tmp_path: Path) -> None:
    project = cpp_generate(tmp_path, "example")
    assert (project / "CMakeLists.txt").is_file()
    assert (project / "cmake" / "besa" / "besaConfig.cmake").is_file()
    assert (project / "cmake" / "besa" / ".besa-cmake-module").is_file()
    assert (project / "src" / "cpp" / "include" / "example" / "example.hpp").is_file()


def test_cpp_generate_accepts_explicit_spdx_license(tmp_path: Path) -> None:
    project = cpp_generate(tmp_path, "example_mit", "MIT")
    header = project / "src" / "cpp" / "include" / "example_mit" / "example_mit.hpp"
    text = header.read_text(encoding="utf-8")
    assert "SPDX-License-Identifier: MIT" in text
    assert "SPDX-License-Identifier: Apache-2.0" not in text


def test_cpp_generate_cli_prompts_for_spdx_license_when_interactive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class InteractiveInput:
        @staticmethod
        def isatty() -> bool:
            return True

    monkeypatch.setattr(cli.sys, "stdin", InteractiveInput())
    monkeypatch.setattr("builtins.input", lambda prompt: "BSD-3-Clause")

    assert (
        main(
            [
                "cpp",
                "generate",
                "--path",
                str(tmp_path),
                "--name",
                "example_bsd",
            ]
        )
        == 0
    )
    header = tmp_path / "example_bsd" / "src" / "cpp" / "include" / "example_bsd" / "example_bsd.hpp"
    assert "SPDX-License-Identifier: BSD-3-Clause" in header.read_text(encoding="utf-8")


def test_cpp_generate_cli_uses_apache_default_noninteractively(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class NonInteractiveInput:
        @staticmethod
        def isatty() -> bool:
            return False

    monkeypatch.setattr(cli.sys, "stdin", NonInteractiveInput())

    assert (
        main(
            [
                "cpp",
                "generate",
                "--path",
                str(tmp_path),
                "--name",
                "example_default_license",
            ]
        )
        == 0
    )
    header = (
        tmp_path
        / "example_default_license"
        / "src"
        / "cpp"
        / "include"
        / "example_default_license"
        / "example_default_license.hpp"
    )
    assert "SPDX-License-Identifier: Apache-2.0" in header.read_text(encoding="utf-8")


def test_cpp_update_replaces_only_managed_directory(tmp_path: Path) -> None:
    project = cpp_generate(tmp_path, "example")
    module = project / "cmake" / "besa"
    (module / "stale.cmake").write_text("stale", encoding="utf-8")
    updated = cpp_update(project)
    assert updated == module
    assert not (module / "stale.cmake").exists()


def test_cpp_update_supports_custom_relative_module_path(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    destination = cpp_update(project, "bs/besa")
    assert destination == project / "bs" / "besa"
    assert (destination / "besaConfig.cmake").is_file()


def test_cpp_update_refuses_unmanaged_directory(tmp_path: Path) -> None:
    project = tmp_path / "project"
    destination = project / "cmake" / "besa"
    destination.mkdir(parents=True)
    (destination / "important.txt").write_text("do not delete", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Refusing to replace"):
        cpp_update(project)


def test_python_generate_uses_current_directory_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "example_python"
    project.mkdir()
    monkeypatch.chdir(project)
    generated = python_generate()
    assert generated == project
    assert (project / "pyproject.toml").is_file()
    assert not (project / "pyproject.toml.in").exists()
    assert (project / "src" / "example_python" / "__init__.py").is_file()


def test_parent_commands_show_help(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "{cpp,python}" in capsys.readouterr().out
    assert main(["cpp"]) == 0
    assert "{generate,update}" in capsys.readouterr().out
    assert main(["python"]) == 0
    assert "{generate}" in capsys.readouterr().out
