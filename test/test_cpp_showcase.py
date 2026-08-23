# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from besa.cli import cpp_generate


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        pytest.fail(
            f"Command failed with exit code {result.returncode}: {' '.join(command)}\n\n"
            f"{result.stdout}",
            pytrace=False,
        )
    return result


@pytest.mark.cpp
def test_generated_cpp_project_builds_hello_showcase(tmp_path: Path) -> None:
    if shutil.which("cmake") is None or shutil.which("g++") is None:
        pytest.skip("CMake and g++ are required")

    project = cpp_generate(tmp_path, "example_showcase")
    showcase = project / "showcases" / "hello"
    assert (showcase / "CMakeLists.txt").is_file()
    assert (showcase / "hello.cpp").is_file()
    assert not (project / "showcase").exists()

    root_cmake = (project / "CMakeLists.txt").read_text(encoding="utf-8")
    assert '  NAME showcases\n  WHEN REGEX "^showcase-"' in root_cmake

    build = project / "build-showcase"
    _run(
        [
            "cmake",
            "-S",
            ".",
            "-B",
            str(build),
            "-DPROJECT_FEATURES=showcase-hello",
            "-DRELEASE_TYPE=release",
        ],
        project,
    )
    _run(["cmake", "--build", str(build), "--target", "showcase.hello"], project)
    result = _run([str(build / "showcases" / "hello" / "showcase-hello")], project)
    assert result.stdout == "Hello world from showcase\n"
