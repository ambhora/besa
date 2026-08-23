# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

import json
import os
import runpy

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
    assert project == tmp_path / "main"
    assert (project / "CMakeLists.txt").is_file()
    assert (project / "cmake" / "besa" / "besaConfig.cmake").is_file()
    assert (project / "cmake" / "besa" / "generated.cmake").is_file()
    assert (project / "cmake" / "besa" / ".besa-cmake-module").is_file()
    header = project / "src" / "cpp" / "include" / "example" / "example.hpp"
    assert header.is_file()
    header_text = header.read_text(encoding="utf-8")
    assert "#ifndef EXAMPLE_EXAMPLE_HPP" in header_text
    assert "#define EXAMPLE_EXAMPLE_HPP" in header_text
    assert "#pragma once" not in header_text
    assert not (project / ".nvimrc").exists()
    assert not (project / ".ycm_extra_conf.py").exists()


def test_cpp_generate_accepts_explicit_spdx_license(tmp_path: Path) -> None:
    license_text = tmp_path / "MIT.txt"
    license_text.write_text("MIT License\n", encoding="utf-8")
    project = cpp_generate(tmp_path, "example_mit", "MIT", license_text=license_text)
    header = project / "src" / "cpp" / "include" / "example_mit" / "example_mit.hpp"
    text = header.read_text(encoding="utf-8")
    assert "SPDX-License-" "Identifier: MIT" in text
    assert "SPDX-License-" "Identifier: Apache-2.0" not in text
    properdocs = (project / "properdocs.yml").read_text(encoding="utf-8")
    assert "Copyright &copy; example_mit developers &middot; MIT" in properdocs
    assert "BESA_PROJECT_LICENSE" not in properdocs


def test_cpp_generate_cli_accepts_license_option(tmp_path: Path) -> None:
    license_text = tmp_path / "BSD-3-Clause.txt"
    license_text.write_text("BSD 3-Clause License\n", encoding="utf-8")
    assert (
        main(
            [
                "cpp",
                "generate",
                "--path",
                str(tmp_path),
                "--name",
                "example_bsd",
                "--license",
                "BSD-3-Clause",
                "--license-text",
                str(license_text),
            ]
        )
        == 0
    )
    header = tmp_path / "main" / "src" / "cpp" / "include" / "example_bsd" / "example_bsd.hpp"
    assert "SPDX-License-" "Identifier: BSD-3-Clause" in header.read_text(encoding="utf-8")


def test_cpp_generate_cli_defaults_to_main_and_apache_without_stdin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_input(prompt: str) -> str:
        raise AssertionError(f"unexpected stdin prompt: {prompt}")

    monkeypatch.setattr("builtins.input", fail_input)

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
        / "main"
        / "src"
        / "cpp"
        / "include"
        / "example_default_license"
        / "example_default_license.hpp"
    )
    assert "SPDX-License-" "Identifier: Apache-2.0" in header.read_text(encoding="utf-8")


def test_cpp_generate_cli_accepts_custom_directory(tmp_path: Path) -> None:
    assert (
        main(
            [
                "cpp",
                "generate",
                "--path",
                str(tmp_path),
                "--name",
                "example_custom_directory",
                "--directory",
                "code",
            ]
        )
        == 0
    )
    assert (tmp_path / "code" / "CMakeLists.txt").is_file()
    assert (
        tmp_path
        / "code"
        / "src"
        / "cpp"
        / "include"
        / "example_custom_directory"
        / "example_custom_directory.hpp"
    ).is_file()


def test_cpp_generate_cli_can_install_gitignored_nvim_ycm_config(tmp_path: Path) -> None:
    license_text = tmp_path / "MIT.txt"
    license_text.write_text("MIT License\n", encoding="utf-8")
    assert (
        main(
            [
                "cpp",
                "generate",
                "--path",
                str(tmp_path),
                "--name",
                "example_editor",
                "--license",
                "MIT",
                "--license-text",
                str(license_text),
                "--nvim-ycm",
            ]
        )
        == 0
    )

    project = tmp_path / "main"
    nvimrc = project / ".nvimrc"
    ycm = project / ".ycm_extra_conf.py"
    gitignore = (project / ".gitignore").read_text(encoding="utf-8")

    assert nvimrc.is_file()
    assert ycm.is_file()
    assert ".nvimrc" in gitignore.splitlines()
    assert ".ycm_extra_conf.py" in gitignore.splitlines()
    assert "SPDX-License-" "Identifier: MIT" in nvimrc.read_text(encoding="utf-8")
    assert "SPDX-License-" "Identifier: MIT" in ycm.read_text(encoding="utf-8")
    assert 'call s:insert_license_slash()' in nvimrc.read_text(encoding="utf-8")
    assert 'call s:insert_license_cpp()' not in nvimrc.read_text(encoding="utf-8")
    assert '"-std=c++26"' in ycm.read_text(encoding="utf-8")
    assert '"src", "**", "include"' in ycm.read_text(encoding="utf-8")
    assert 'compile_commands.json' in ycm.read_text(encoding="utf-8")


def test_generated_ycm_uses_source_analogue_compile_commands_for_headers(tmp_path: Path) -> None:
    project = cpp_generate(tmp_path, "example_ycm_analogue", nvim_ycm=True)
    source = (
        project
        / "src"
        / "cpp"
        / "lib"
        / "example_ycm_analogue"
        / "example_ycm_analogue.cpp"
    )
    header = (
        project
        / "src"
        / "cpp"
        / "include"
        / "example_ycm_analogue"
        / "example_ycm_analogue.hpp"
    )

    source_include = project / "dependency" / "source"
    unrelated_include = project / "dependency" / "unrelated"
    source_include.mkdir(parents=True)
    unrelated_include.mkdir(parents=True)

    cuda_header = project / "src" / "cuda" / "include" / "example_ycm_analogue" / "kernel.hpp"
    cuda_source = project / "src" / "cuda" / "lib" / "example_ycm_analogue" / "kernel.cu"
    cuda_header.parent.mkdir(parents=True)
    cuda_source.parent.mkdir(parents=True)
    cuda_header.write_text("#pragma once\n", encoding="utf-8")
    cuda_source.write_text("", encoding="utf-8")

    build = tmp_path / "build"
    build.mkdir()
    (build / "compile_commands.json").write_text(
        json.dumps(
            [
                {
                    "directory": str(project),
                    "file": str(source),
                    "arguments": [
                        "clang++",
                        "-std=c++26",
                        "-DEXACT_SOURCE=1",
                        "-I",
                        str(source_include.relative_to(project)),
                        "-c",
                        str(source),
                        "-o",
                        "source.o",
                    ],
                },
                {
                    "directory": str(project),
                    "file": str(project / "other.cpp"),
                    "arguments": [
                        "clang++",
                        "-DUNRELATED_SOURCE=1",
                        "-I",
                        str(unrelated_include.relative_to(project)),
                        "-c",
                        str(project / "other.cpp"),
                        "-o",
                        "other.o",
                    ],
                },
                {
                    "directory": str(project),
                    "file": str(cuda_source),
                    "arguments": [
                        "clang++",
                        "-x",
                        "cuda",
                        "-DCUDA_SOURCE=1",
                        "-c",
                        str(cuda_source),
                        "-o",
                        "kernel.o",
                    ],
                },
            ]
        ),
        encoding="utf-8",
    )

    settings = runpy.run_path(str(project / ".ycm_extra_conf.py"))["Settings"]

    source_flags = settings(str(source))["flags"]
    assert "-Weverything" in source_flags
    assert "-std=c++26" in source_flags
    assert "-DEXACT_SOURCE=1" in source_flags
    assert "-I" in source_flags
    assert str(source_include) in source_flags
    assert "-DUNRELATED_SOURCE=1" not in source_flags
    assert str(unrelated_include) not in source_flags
    assert "-c" not in source_flags
    assert "source.o" not in source_flags

    header_flags = settings(str(header))["flags"]
    assert "-DEXACT_SOURCE=1" in header_flags
    assert str(source_include) in header_flags
    assert "-DUNRELATED_SOURCE=1" not in header_flags
    assert str(unrelated_include) not in header_flags

    cuda_header_flags = settings(str(cuda_header))["flags"]
    assert "-DCUDA_SOURCE=1" in cuda_header_flags
    assert "cuda" in cuda_header_flags


def test_generated_ycm_uses_c17_baseline_for_c_headers_without_compile_entry(tmp_path: Path) -> None:
    project = cpp_generate(tmp_path, "example_ycm_c", nvim_ycm=True)
    header = project / "src" / "c" / "include" / "example_ycm_c" / "example_ycm_c.h"
    header.parent.mkdir(parents=True)
    header.write_text("#pragma once\n", encoding="utf-8")

    settings = runpy.run_path(str(project / ".ycm_extra_conf.py"))["Settings"]
    flags = settings(str(header))["flags"]

    assert "-std=c17" in flags
    assert "-x" in flags
    assert "c" in flags
    assert "-std=c++26" not in flags


def test_generated_ycm_fallback_discovers_all_generator_include_roots(tmp_path: Path) -> None:
    project = cpp_generate(tmp_path, "example_ycm_generated", nvim_ycm=True)
    header = project / "scratch" / "unmatched.hpp"
    header.parent.mkdir(parents=True)
    header.write_text("#ifndef UNMATCHED_HPP\n#define UNMATCHED_HPP\n#endif\n", encoding="utf-8")

    meta = project / "build" / "debug" / "generated" / "meta" / "include"
    schema = project / "build" / "debug" / "generated" / "schema" / "include"
    meta.mkdir(parents=True)
    schema.mkdir(parents=True)

    settings = runpy.run_path(str(project / ".ycm_extra_conf.py"))["Settings"]
    flags = settings(str(header))["flags"]

    assert "-I" + str(meta) in flags
    assert "-I" + str(schema) in flags


def test_generated_ycm_adds_active_spack_view_include_as_isystem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = cpp_generate(tmp_path, "example_ycm_spack", nvim_ycm=True)
    header = (
        project
        / "src"
        / "cpp"
        / "include"
        / "example_ycm_spack"
        / "example_ycm_spack.hpp"
    )

    view = tmp_path / "spack-view"
    include = view / "include"
    include.mkdir(parents=True)

    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    spack = bin_directory / "spack"
    spack.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "location" ] && [ "$2" = "-v" ]; then\n'
        '  printf "%s\\n" "$FAKE_SPACK_VIEW"\n'
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
        encoding="utf-8",
    )
    spack.chmod(0o755)

    monkeypatch.setenv("SPACK_ENV", str(project))
    monkeypatch.setenv("SPACK_ENV_VIEW", "default")
    monkeypatch.setenv("FAKE_SPACK_VIEW", str(view))
    monkeypatch.setenv(
        "PATH",
        str(bin_directory) + os.pathsep + os.environ.get("PATH", ""),
    )

    settings = runpy.run_path(str(project / ".ycm_extra_conf.py"))["Settings"]
    flags = settings(str(header))["flags"]

    assert "-isystem" in flags
    isystem_index = flags.index("-isystem")
    assert flags[isystem_index + 1] == str(include)


def test_cpp_generate_rejects_nested_directory_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="single relative path component"):
        cpp_generate(tmp_path, "example", directory="nested/main")


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
