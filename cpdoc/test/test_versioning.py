# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
import shutil

import pytest

from cpdoc.versioning import selected_ref_names


def _run(command: list[str], cwd: Path) -> None:
    import subprocess

    subprocess.run(command, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def test_version_selectors_choose_semantic_tags_and_exact_refs(tmp_path: Path) -> None:
    if shutil.which("git") is None:
        pytest.skip("Git is required")
    project = tmp_path / "project"
    project.mkdir()
    _run(["git", "init", "-b", "main"], project)
    _run(["git", "config", "user.email", "cpdoc-test@example.invalid"], project)
    _run(["git", "config", "user.name", "cpdoc Test"], project)
    (project / "readme.md").write_text("test\n", encoding="utf-8")
    _run(["git", "add", "."], project)
    _run(["git", "commit", "-m", "initial"], project)
    for tag in ("v0.8.0", "v0.9.0", "v0.10.0", "v0.11.0-rc.1", "v0.11.0", "nightly"):
        _run(["git", "tag", tag], project)
    _run(["git", "branch", "maintenance"], project)

    assert selected_ref_names(project, "all") == [
        "main", "v0.11.0", "v0.11.0-rc.1", "v0.10.0", "v0.9.0", "v0.8.0"
    ]
    assert selected_ref_names(project, "latest:3") == [
        "main", "v0.11.0", "v0.11.0-rc.1", "v0.10.0"
    ]
    assert selected_ref_names(project, "range:>=0.9,<0.11") == [
        "main", "v0.11.0-rc.1", "v0.10.0", "v0.9.0"
    ]
    assert selected_ref_names(project, "refs:v0.8.0,maintenance") == [
        "main", "v0.8.0", "maintenance"
    ]
    with pytest.raises(RuntimeError, match="unknown cpdoc Git refs"):
        selected_ref_names(project, "refs:v9.9.9")
