# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
"""High-level cpdoc build operations."""

from __future__ import annotations

import dataclasses
import json
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

from .config import CpdocConfig
from .cpp_backend import build_cpp_graph
from .html_renderer import render_html_site
from .model import ApiGraph
from .python_backend import build_python_graph
from .rust_backend import build_rust_graph
from .versioning import selected_ref_names


def _graph_json(graph: ApiGraph) -> str:
    return json.dumps(dataclasses.asdict(graph), indent=2, sort_keys=True) + "\n"


def _project_docs_url(graph: ApiGraph, configured: str, *, root_depth: int = 2) -> str:
    if configured != "auto":
        return configured
    version_depth = max(1, len(PurePosixPath(graph.version).parts))
    return "../" * (root_depth + version_depth)


def _copyright(config: CpdocConfig, graph: ApiGraph) -> str:
    return config.copyright_text or f"Copyright © {graph.project} developers"


def _render(
    graph: ApiGraph,
    config: CpdocConfig,
    *,
    output: Path,
    work: Path,
    project_docs_root_depth: int = 2,
) -> None:
    work.mkdir(parents=True, exist_ok=True)
    render_html_site(
        graph,
        output_directory=output,
        project_docs_url=_project_docs_url(
            graph, config.project_docs_url, root_depth=project_docs_root_depth
        ),
        copyright_text=_copyright(config, graph),
        introduction_file=config.content_index,
    )
    (work / "api-graph.json").write_text(_graph_json(graph), encoding="utf-8")


def _build_cpp(config: CpdocConfig, *, project_root: Path, work: Path, version: str) -> ApiGraph:
    if config.provider != "besa":
        raise RuntimeError(
            f"cpdoc C++ provider {config.provider!r} is not available; currently supported: 'besa'"
        )
    return build_cpp_graph(
        project_root=project_root,
        work_directory=work / "extract",
        version=version,
        cmake=config.cmake,
        clang=config.clang,
        only_profiles=set(config.variants) if config.variants else None,
    )


def build_current(
    config: CpdocConfig,
    *,
    output_directory: Path | None = None,
    work_directory: Path | None = None,
    version: str = "main",
    project_docs_root_depth: int = 2,
) -> ApiGraph:
    """Build the current checkout described by ``config``."""

    output = (output_directory or config.output_current).resolve()
    work = (work_directory or config.work_directory / "current").resolve()
    if config.language == "cpp":
        graph = _build_cpp(config, project_root=config.project_root, work=work, version=version)
    elif config.language == "python":
        raise RuntimeError("cpdoc.yml Python project configuration is not implemented yet")
    elif config.language == "rust":
        raise RuntimeError("cpdoc.yml Rust project configuration is not implemented yet")
    else:
        raise RuntimeError(f"unsupported cpdoc language {config.language!r}")
    _render(
        graph,
        config,
        output=output,
        work=work / "render",
        project_docs_root_depth=project_docs_root_depth,
    )
    return graph


def _html_pages(root: Path) -> list[str]:
    if not root.is_dir():
        return []
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*.html"))


def _write_versions(output: Path, refs: list[str], default: str) -> None:
    metadata = {
        "default": default,
        "versions": [
            {"name": name, "url": f"{name}/", "pages": _html_pages(output / name)}
            for name in refs
            if (output / name / "index.html").is_file()
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "versions.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def _git(command: list[str], *, cwd: Path) -> None:
    result = subprocess.run(
        ["git", *command],
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        raise RuntimeError("Git command failed:\n" + result.stdout.rstrip())


def build_versions(
    config: CpdocConfig,
    *,
    output_directory: Path | None = None,
    work_directory: Path | None = None,
    selector: str | None = None,
    project_docs_root_depth: int = 2,
) -> list[str]:
    """Build selected Git refs into one versioned cpdoc tree."""

    project_root = config.project_root.resolve()
    selected = selected_ref_names(project_root, selector or config.versions_selector)
    output = (output_directory or config.output_versions).resolve()
    work_root = (work_directory or config.work_directory / "versions").resolve()
    shutil.rmtree(output, ignore_errors=True)
    output.mkdir(parents=True, exist_ok=True)

    built: list[str] = []
    for ref in selected:
        if ref == "main":
            checkout = project_root
            cleanup = None
        else:
            temporary = tempfile.TemporaryDirectory(prefix="cpdoc-ref-")
            checkout = Path(temporary.name) / "checkout"
            _git(["worktree", "add", "--detach", str(checkout), ref], cwd=project_root)
            cleanup = temporary
        try:
            ref_work = work_root / ref.replace("/", "__")
            if config.language != "cpp":
                raise RuntimeError("versioned cpdoc builds currently require the C++ backend")
            graph = _build_cpp(config, project_root=checkout, work=ref_work, version=ref)
            _render(
                graph,
                config,
                output=output / ref,
                work=ref_work / "render",
                project_docs_root_depth=project_docs_root_depth,
            )
            built.append(ref)
        finally:
            if ref != "main":
                _git(["worktree", "remove", "--force", str(checkout)], cwd=project_root)
                assert cleanup is not None
                cleanup.cleanup()

    default = config.default_version if config.default_version in built else (built[0] if built else "main")
    _write_versions(output, built, default)
    return built


__all__ = ["build_current", "build_versions", "build_python_graph", "build_rust_graph"]
