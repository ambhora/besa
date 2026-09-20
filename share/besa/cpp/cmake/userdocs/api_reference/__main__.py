# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
"""Command-line driver for BESA semantic API references."""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import shutil
import tempfile
from pathlib import Path, PurePosixPath

from .cpp_backend import build_cpp_graph
from .html_renderer import render_html_site
from .model import ApiGraph
from .python_backend import build_python_graph
from .rust_backend import build_rust_graph
from .versioning import selected_ref_names, selector


def _copyright(project_root: Path, project: str) -> str:
    config = project_root / "properdocs.yml"
    if config.is_file():
        match = re.search(r"^copyright:\s*(.+?)\s*$", config.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            value = match.group(1).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            return value
    return f"Copyright © {project} developers"


def _graph_json(graph: ApiGraph) -> str:
    return json.dumps(dataclasses.asdict(graph), indent=2, sort_keys=True) + "\n"


def _render_graph(
    graph: ApiGraph,
    *,
    project_root: Path,
    work_directory: Path,
    output_directory: Path,
    template_directory: Path,
    properdocs: str,
    project_docs_url: str,
) -> None:
    del properdocs
    render_root = work_directory / "render"
    render_root.mkdir(parents=True, exist_ok=True)
    effective_project_docs_url = project_docs_url
    if project_docs_url == "auto":
        # Published API versions live below reference/api/<ref>/. A ref containing slashes adds
        # one directory level per path component, so derive the project-site link from the version
        # name rather than baking page-specific ../../ chains into generated templates.
        version_depth = max(1, len(PurePosixPath(graph.version).parts))
        effective_project_docs_url = "../" * (2 + version_depth)
    render_html_site(
        graph,
        output_directory=output_directory,
        project_docs_url=effective_project_docs_url,
        copyright_text=_copyright(project_root, graph.project),
        template_directory=template_directory,
    )
    (render_root / "api-graph.json").write_text(_graph_json(graph), encoding="utf-8")


def _build_cpp(arguments: argparse.Namespace) -> ApiGraph:
    return build_cpp_graph(
        project_root=arguments.project_root,
        work_directory=arguments.work_directory / "extract",
        version=arguments.version,
        cmake=arguments.cmake,
        clang=arguments.clang,
        only_profiles=set(arguments.profile) if arguments.profile else None,
    )


def _build_single(arguments: argparse.Namespace) -> int:
    project_root = arguments.project_root.resolve()
    if arguments.language == "cpp":
        graph = _build_cpp(arguments)
    elif arguments.language == "python":
        graph = build_python_graph(
            project_root=project_root,
            package_root=arguments.package_root,
            package=arguments.package,
            version=arguments.version,
        )
    else:
        graph = build_rust_graph(
            rustdoc_json=arguments.rustdoc_json,
            project=arguments.project,
            version=arguments.version,
            project_root=project_root,
        )
    _render_graph(
        graph,
        project_root=project_root,
        work_directory=arguments.work_directory,
        output_directory=arguments.output_directory,
        template_directory=arguments.template_directory,
        properdocs=arguments.properdocs,
        project_docs_url=arguments.project_docs_url,
    )
    return 0


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


def _build_versions(arguments: argparse.Namespace) -> int:
    project_root = arguments.project_root.resolve()
    selected = selected_ref_names(project_root, selector(project_root))
    output = arguments.output_directory.resolve()
    shutil.rmtree(output, ignore_errors=True)
    output.mkdir(parents=True, exist_ok=True)

    built: list[str] = []
    for ref in selected:
        if ref == "main":
            checkout = project_root
            cleanup = None
        else:
            temporary = tempfile.TemporaryDirectory(prefix="besa-api-ref-")
            checkout = Path(temporary.name) / "checkout"
            _git(["worktree", "add", "--detach", str(checkout), ref], cwd=project_root)
            cleanup = temporary
        try:
            namespace = argparse.Namespace(**vars(arguments))
            namespace.language = "cpp"
            namespace.project_root = checkout
            namespace.version = ref
            namespace.work_directory = arguments.work_directory / "versions" / ref.replace("/", "__")
            namespace.output_directory = output / ref
            graph = _build_cpp(namespace)
            _render_graph(
                graph,
                project_root=checkout,
                work_directory=namespace.work_directory,
                output_directory=namespace.output_directory,
                template_directory=arguments.template_directory,
                properdocs=arguments.properdocs,
                project_docs_url=arguments.project_docs_url,
            )
            built.append(ref)
        finally:
            if ref != "main":
                _git(["worktree", "remove", "--force", str(checkout)], cwd=project_root)
                assert cleanup is not None
                cleanup.cleanup()

    default = arguments.default_version if arguments.default_version in built else (built[0] if built else "main")
    _write_versions(output, built, default)
    return 0


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--work-directory", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--template-directory", type=Path, required=True)
    # Retained as an accepted compatibility option because older generated CMake files still pass
    # it.  The semantic API reference is rendered directly to HTML and no longer invokes
    # ProperDocs/Sphinx/Doxygen.
    parser.add_argument("--properdocs", default="")
    parser.add_argument("--project-docs-url", default="auto")
    parser.add_argument("--version", default="main")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build BESA semantic API reference sites")
    commands = parser.add_subparsers(dest="command", required=True)

    cpp = commands.add_parser("build-cpp")
    _common(cpp)
    cpp.set_defaults(language="cpp")
    cpp.add_argument("--cmake", default="cmake")
    cpp.add_argument("--clang", default="clang++")
    cpp.add_argument("--profile", action="append", default=[])

    python = commands.add_parser("build-python")
    _common(python)
    python.set_defaults(language="python")
    python.add_argument("--package-root", type=Path, required=True)
    python.add_argument("--package", required=True)

    rust = commands.add_parser("build-rust")
    _common(rust)
    rust.set_defaults(language="rust")
    rust.add_argument("--rustdoc-json", type=Path, required=True)
    rust.add_argument("--project", required=True)

    versions = commands.add_parser("build-versions")
    _common(versions)
    versions.add_argument("--cmake", default="cmake")
    versions.add_argument("--clang", default="clang++")
    versions.add_argument("--profile", action="append", default=[])
    versions.add_argument("--default-version", default="main")

    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "build-versions":
            return _build_versions(arguments)
        return _build_single(arguments)
    except RuntimeError as error:
        parser.exit(2, f"besa api reference: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
