# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from besa.cli import python_generate


@pytest.mark.python
def test_python_template_generates_and_tests(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "example_python"
    project.mkdir()
    monkeypatch.chdir(project)
    python_generate()

    subprocess.run([sys.executable, "-m", "compileall", "-q", "src"], check=True)
    # The repository-level pytest installation can exercise the generated package without requiring
    # network access or a second environment.
    env = {**__import__("os").environ, "PYTHONPATH": str(project / "src")}
    subprocess.run([sys.executable, "-m", "pytest", "-q", "test"], env=env, check=True)
