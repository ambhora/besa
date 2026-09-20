# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path

from cpdoc import build as build_module
from cpdoc.config import CpdocConfig
from cpdoc.model import ApiGraph


def _config(tmp_path: Path) -> CpdocConfig:
    return CpdocConfig(
        config_file=tmp_path / "cpdoc.yml",
        project_root=tmp_path / "project",
        provider="besa",
        language="cpp",
        content_index=None,
        output_current=tmp_path / "current",
        output_versions=tmp_path / "versions",
        work_directory=tmp_path / "work",
        project_docs_url="auto",
        copyright_text=None,
        versions_selector="all",
        default_version="main",
        cmake="cmake",
        clang="clang++",
        variants=(),
    )


def test_version_builder_uses_git_worktrees(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    config.project_root.mkdir()
    monkeypatch.setattr(build_module, "selected_ref_names", lambda _root, _selector: ["main", "v1.0.0"])

    git_calls: list[list[str]] = []
    def fake_git(command: list[str], *, cwd: Path) -> None:
        git_calls.append(command)
        if command[:2] == ["worktree", "add"]:
            Path(command[-2]).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(build_module, "_git", fake_git)

    built: list[tuple[str, Path]] = []
    def fake_build_cpp(config, *, project_root: Path, work: Path, version: str):
        del config, work
        built.append((version, project_root))
        return ApiGraph(project="example", version=version, language="cpp")
    monkeypatch.setattr(build_module, "_build_cpp", fake_build_cpp)

    def fake_render(graph, config, *, output: Path, work: Path, project_docs_root_depth: int = 2):
        del config, work, project_docs_root_depth
        output.mkdir(parents=True, exist_ok=True)
        (output / "index.html").write_text(graph.version, encoding="utf-8")
    monkeypatch.setattr(build_module, "_render", fake_render)

    assert build_module.build_versions(config) == ["main", "v1.0.0"]
    assert built[0] == ("main", config.project_root.resolve())
    assert built[1][0] == "v1.0.0" and built[1][1] != config.project_root.resolve()
    assert git_calls[0][:3] == ["worktree", "add", "--detach"]
    assert git_calls[-1][:3] == ["worktree", "remove", "--force"]


def test_versions_metadata_contains_nested_pages(tmp_path: Path) -> None:
    output = tmp_path / "api"
    for version in ("main", "1.0.0", "release/3.0"):
        (output / version).mkdir(parents=True)
        (output / version / "index.html").write_text(version, encoding="utf-8")
    (output / "main" / "detail").mkdir()
    (output / "main" / "detail" / "index.html").write_text("detail", encoding="utf-8")

    refs = ["main", "1.0.0", "release/3.0"]
    build_module._write_versions(output, refs, "main")
    metadata = json.loads((output / "versions.json").read_text(encoding="utf-8"))
    assert metadata["default"] == "main"
    assert metadata["versions"][0] == {
        "name": "main", "url": "main/", "pages": ["detail/index.html", "index.html"]
    }
    assert {item["name"] for item in metadata["versions"]} == set(refs)
    assert not (output / "index.html").exists()
