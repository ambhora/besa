# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
"""Configuration loading for cpdoc."""

from __future__ import annotations

from dataclasses import dataclass, replace
import os
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class CpdocConfig:
    """Resolved, path-normalized cpdoc configuration."""

    config_file: Path
    project_root: Path
    provider: str
    language: str
    content_index: Path | None
    output_current: Path
    output_versions: Path
    work_directory: Path
    project_docs_url: str
    copyright_text: str | None
    versions_selector: str
    default_version: str
    cmake: str
    clang: str
    variants: tuple[str, ...]

    def with_overrides(
        self,
        *,
        output_directory: Path | None = None,
        work_directory: Path | None = None,
        version: str | None = None,
        project_docs_url: str | None = None,
        versions_selector: str | None = None,
    ) -> "CpdocConfig":
        values: dict[str, object] = {}
        if output_directory is not None:
            values["output_current"] = output_directory.resolve()
        if work_directory is not None:
            values["work_directory"] = work_directory.resolve()
        if project_docs_url is not None:
            values["project_docs_url"] = project_docs_url
        if versions_selector is not None:
            values["versions_selector"] = versions_selector
        # ``version`` belongs to one build invocation rather than the persistent config, but the
        # argument is accepted here so CLI callers can use one override helper consistently.
        del version
        return replace(self, **values)


def _mapping(value: object, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise RuntimeError(f"cpdoc.yml: {name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _resolve(base: Path, value: object, default: str) -> Path:
    path = Path(str(value or default)).expanduser()
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def load_config(path: Path | str = "cpdoc.yml") -> CpdocConfig:
    """Load ``cpdoc.yml`` and resolve all project-relative paths."""

    config_file = Path(path).expanduser().resolve()
    if not config_file.is_file():
        raise RuntimeError(f"cpdoc configuration does not exist: {config_file}")
    raw = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise RuntimeError("cpdoc.yml: top level must be a mapping")
    schema = raw.get("schema", 1)
    if schema != 1:
        raise RuntimeError(f"cpdoc.yml: unsupported schema {schema!r}")

    base = config_file.parent
    project = _mapping(raw.get("project"), "project")
    content = _mapping(raw.get("content"), "content")
    output = _mapping(raw.get("output"), "output")
    links = _mapping(raw.get("links"), "links")
    versions = _mapping(raw.get("versions"), "versions")
    cpp = _mapping(raw.get("cpp"), "cpp")

    project_root = _resolve(base, project.get("root"), ".")
    content_index_value = content.get("index")
    content_index = (
        _resolve(base, content_index_value, "api-docs/index.md")
        if content_index_value is not None
        else None
    )
    variants_value = cpp.get("variants", [])
    if variants_value is None:
        variants_value = []
    if not isinstance(variants_value, list):
        raise RuntimeError("cpdoc.yml: cpp.variants must be a list")

    selector = str(
        os.environ.get("CPDOC_VERSIONS")
        or versions.get("select")
        or "all"
    ).strip()

    copyright_value = project.get("copyright")
    return CpdocConfig(
        config_file=config_file,
        project_root=project_root,
        provider=str(project.get("provider") or "besa"),
        language=str(project.get("language") or "cpp"),
        content_index=content_index,
        output_current=_resolve(base, output.get("current"), "build/doc/api/current"),
        output_versions=_resolve(base, output.get("versions"), "build/doc/api/versions"),
        work_directory=_resolve(base, output.get("work"), "build/doc/work/cpdoc"),
        project_docs_url=str(links.get("project-docs") or "auto"),
        copyright_text=str(copyright_value) if copyright_value is not None else None,
        versions_selector=selector,
        default_version=str(versions.get("default") or "main"),
        cmake=str(cpp.get("cmake") or "cmake"),
        clang=str(cpp.get("clang") or "clang++"),
        variants=tuple(str(value) for value in variants_value if str(value)),
    )
