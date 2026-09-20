# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
"""Framework-independent helpers used by the ProperDocs cpdoc plugin."""

from __future__ import annotations

import posixpath
import re
import shutil
from pathlib import Path, PurePosixPath
from urllib.parse import quote

_APIDOCS_REFERENCE = re.compile(
    r"@apidocs(?:\[(?P<version>[^\]]+)\])?::(?P<symbol>[A-Za-z_][A-Za-z0-9_:.]*)"
)


def repository_provider(repo_url: str, extra: dict[str, object]) -> str:
    explicit = str(extra.get("besa_repo_provider") or "").strip().lower()
    if explicit:
        return explicit
    host = repo_url.lower()
    if "github" in host:
        return "github"
    if "bitbucket" in host:
        return "bitbucket"
    return "gitlab"


def _repository_base(repo_url: str) -> str:
    value = repo_url.rstrip("/")
    return value[:-4] if value.endswith(".git") else value


def source_url(repo_url: str, provider: str, ref: str, source_path: str) -> str:
    base = _repository_base(repo_url)
    ref_part = quote(ref, safe="/")
    path_part = quote(source_path, safe="/")
    if provider == "github":
        return f"{base}/blob/{ref_part}/{path_part}"
    if provider == "bitbucket":
        return f"{base}/src/{ref_part}/{path_part}"
    return f"{base}/-/blob/{ref_part}/{path_part}"


def edit_url(repo_url: str, provider: str, ref: str, source_path: str) -> str:
    base = _repository_base(repo_url)
    ref_part = quote(ref, safe="/")
    path_part = quote(source_path, safe="/")
    if provider == "github":
        return f"{base}/edit/{ref_part}/{path_part}"
    if provider == "bitbucket":
        return f"{base}/src/{ref_part}/{path_part}?mode=edit"
    return f"{base}/-/edit/{ref_part}/{path_part}"


def default_issue_url(repo_url: str, provider: str) -> str:
    base = _repository_base(repo_url)
    return f"{base}/-/issues/new" if provider == "gitlab" else f"{base}/issues/new"


def api_symbol_public_path(symbol: str, version: str, mount: str) -> PurePosixPath:
    return (
        PurePosixPath(mount)
        / version
        / "_symbols"
        / PurePosixPath(*re.split(r"::|\.", symbol))
    )


def resolve_api_references(
    markdown: str,
    *,
    page_dest_uri: str,
    mount: str,
    default_version: str,
) -> str:
    """Resolve ``@apidocs`` names to cpdoc's stable semantic aliases."""

    page_directory = PurePosixPath(page_dest_uri).parent

    def replace(match: re.Match[str]) -> str:
        symbol = match.group("symbol")
        version = match.group("version") or default_version
        target = api_symbol_public_path(symbol, version, mount)
        href = posixpath.relpath(target.as_posix(), page_directory.as_posix())
        return f"[`{symbol}`]({href}/)"

    return _APIDOCS_REFERENCE.sub(replace, markdown)


def publish_api(source: Path, site_directory: Path, mount: str) -> Path:
    """Replace the mounted API subtree with cpdoc's complete versioned output."""

    destination = site_directory / Path(*PurePosixPath(mount).parts)
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    (site_directory / ".nojekyll").touch()
    return destination
