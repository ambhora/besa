# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
"""Live ProperDocs integration for the complete versioned C/C++ API reference.

This is the default ``properdocs serve`` hook. It keeps historical branch/tag API outputs from
sphinx-multiversion and overlays ``main/`` with the current working-tree API. Therefore uncommitted
source edits remain visible without losing the ability to browse older versions.
"""

from __future__ import annotations

import json
import posixpath
import re
import shutil
import subprocess
from pathlib import Path, PurePosixPath
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parent
PROPERDOCS_WORK_DIRECTORY = PROJECT_ROOT.parent / "build" / "properdocs"
BUILD_DIRECTORY = PROPERDOCS_WORK_DIRECTORY / "cmake"
CURRENT_API_BUILD_DIRECTORY = BUILD_DIRECTORY / "doc" / "api" / "current"
MULTIVERSION_API_BUILD_DIRECTORY = BUILD_DIRECTORY / "doc" / "api" / "multiversion"
API_PUBLIC_PATH = Path("reference") / "api"

_APIDOCS_REFERENCE = re.compile(
    r"@apidocs::(?P<symbol>[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*)"
)

_serve_active = False
_last_source_fingerprint: tuple[tuple[str, int, int], ...] | None = None
_last_refs_fingerprint: tuple[tuple[str, int, int], ...] | None = None


def _fingerprint(paths: Iterable[Path]) -> tuple[tuple[str, int, int], ...]:
    values: list[tuple[str, int, int]] = []
    for path in paths:
        if not path.is_file():
            continue
        stat = path.stat()
        values.append((str(path.relative_to(PROJECT_ROOT)), stat.st_mtime_ns, stat.st_size))
    return tuple(sorted(values))


def _source_files() -> Iterable[Path]:
    for root in (
        PROJECT_ROOT / "src",
        PROJECT_ROOT / "api-docs",
        PROJECT_ROOT / "test" / "base",
    ):
        if root.is_dir():
            yield from (path for path in root.rglob("*") if path.is_file())

    cmake = PROJECT_ROOT / "CMakeLists.txt"
    if cmake.is_file():
        yield cmake

    modules = PROJECT_ROOT / "cmake" / "besa"
    if modules.is_dir():
        yield from (path for path in modules.rglob("*.cmake") if path.is_file())


def _ref_files() -> Iterable[Path]:
    git = PROJECT_ROOT / ".git"
    for path in (git / "HEAD", git / "packed-refs"):
        if path.is_file():
            yield path

    refs = git / "refs"
    if refs.is_dir():
        yield from (path for path in refs.rglob("*") if path.is_file())


def _source_fingerprint() -> tuple[tuple[str, int, int], ...]:
    return _fingerprint(_source_files())


def _refs_fingerprint() -> tuple[tuple[str, int, int], ...]:
    return _fingerprint(_ref_files())


def _configure() -> None:
    subprocess.run(
        [
            "cmake",
            "-S",
            str(PROJECT_ROOT),
            "-B",
            str(BUILD_DIRECTORY),
            "-DPROJECT_FEATURES=user-docs",
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )


def _build(target: str) -> None:
    subprocess.run(
        ["cmake", "--build", str(BUILD_DIRECTORY), "--target", target],
        cwd=PROJECT_ROOT,
        check=True,
    )


def _ensure_multiversion_api() -> None:
    """Refresh only the API portions whose inputs changed."""

    global _last_source_fingerprint, _last_refs_fingerprint

    source_fingerprint = _source_fingerprint()
    refs_fingerprint = _refs_fingerprint()

    rebuild_versions = (
        not MULTIVERSION_API_BUILD_DIRECTORY.is_dir()
        or refs_fingerprint != _last_refs_fingerprint
    )
    rebuild_current = (
        not CURRENT_API_BUILD_DIRECTORY.is_dir()
        or source_fingerprint != _last_source_fingerprint
    )

    if not rebuild_versions and not rebuild_current:
        return

    _configure()
    if rebuild_versions:
        _build("user.docs.multiversion")
        _last_refs_fingerprint = refs_fingerprint
    if rebuild_current:
        _build("user.docs.api")
        _last_source_fingerprint = source_fingerprint


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def _copy_entry(source: Path, destination: Path) -> None:
    _remove_path(destination)
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _html_pages(root: Path) -> list[str]:
    if not root.is_dir():
        return []
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*.html"))


def _ensure_main_metadata(api_root: Path) -> None:
    metadata_path = api_root / "versions.json"
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    else:
        metadata = {"default": "main", "versions": []}

    versions = [item for item in metadata.get("versions", []) if item.get("name") != "main"]
    enriched_versions = []
    for item in versions:
        enriched = dict(item)
        enriched["pages"] = _html_pages(api_root / item.get("url", ""))
        enriched_versions.append(enriched)

    metadata["default"] = "main"
    metadata["versions"] = [
        {"name": "main", "url": "main/", "pages": _html_pages(api_root / "main")},
        *enriched_versions,
    ]
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def _publish_multiversion_api(site_directory: Path) -> None:
    if not MULTIVERSION_API_BUILD_DIRECTORY.is_dir():
        return

    api_root = site_directory / API_PUBLIC_PATH
    api_root.mkdir(parents=True, exist_ok=True)

    # Everything below reference/api/ belongs to the generated versioned API. The canonical
    # ProperDocs entry point is the Versioned API section on reference/index.html.
    for child in tuple(api_root.iterdir()):
        _remove_path(child)

    for source in MULTIVERSION_API_BUILD_DIRECTORY.iterdir():
        _copy_entry(source, api_root / source.name)

    # sphinx-multiversion builds Git refs, so uncommitted edits are not represented there. Overlay
    # main/ with the ordinary Sphinx build of the current checkout to make this a true live preview.
    if CURRENT_API_BUILD_DIRECTORY.is_dir():
        _copy_entry(CURRENT_API_BUILD_DIRECTORY, api_root / "main")

    _ensure_main_metadata(api_root)
    (site_directory / ".nojekyll").touch()


def on_startup(*, command: str, dirty: bool = False, **_kwargs) -> None:
    """Enable this hook only for the long-running development server."""

    del dirty
    global _serve_active
    _serve_active = command == "serve"


def on_pre_build(**_kwargs) -> None:
    if _serve_active:
        _ensure_multiversion_api()


def _api_symbol_public_path(symbol: str, version: str) -> PurePosixPath:
    return (
        PurePosixPath(API_PUBLIC_PATH.as_posix())
        / version
        / "_symbols"
        / PurePosixPath(*symbol.split("::"))
    )


def _api_symbol_build_path(symbol: str, version: str) -> Path:
    root = (
        CURRENT_API_BUILD_DIRECTORY
        if version == "main"
        else MULTIVERSION_API_BUILD_DIRECTORY / version
    )
    return root / "_symbols" / Path(*symbol.split("::")) / "index.html"


def on_page_markdown(markdown, page, config, **_kwargs):
    """Resolve ``@apidocs::qualified::name`` to one selected version of the generated API."""

    if _APIDOCS_REFERENCE.search(markdown) is None:
        return markdown

    version = str(config.get("extra", {}).get("besa_api_version", "main"))
    page_directory = PurePosixPath(page.file.dest_uri).parent

    def replace_reference(match: re.Match[str]) -> str:
        symbol = match.group("symbol")
        # `properdocs serve` builds the API before Markdown rendering, so unresolved references are
        # errors there. A standalone ProperDocs build may intentionally run before API generation;
        # in that mode we still emit the stable semantic URL and let final site assembly provide it.
        if _serve_active and not _api_symbol_build_path(symbol, version).is_file():
            raise RuntimeError(
                f"unresolved API documentation reference {symbol!r} for version {version!r}"
            )

        target = _api_symbol_public_path(symbol, version)
        href = posixpath.relpath(target.as_posix(), page_directory.as_posix())
        return f"[`{symbol}`]({href}/)"

    return _APIDOCS_REFERENCE.sub(replace_reference, markdown)


def on_post_build(config, **_kwargs) -> None:
    if _serve_active:
        _publish_multiversion_api(Path(config["site_dir"]).resolve())
