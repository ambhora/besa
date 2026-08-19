# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
"""Live ProperDocs integration for the current C/C++ API reference.

The hook is active only for ``properdocs serve``. ProperDocs watches ``src/`` and ``api-docs/``;
when those inputs change, the hook configures a small CMake tree with ``user-docs`` enabled, builds
``user.docs.api``, and mounts the result below ``reference/api/main/`` in the served site.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parent
BUILD_DIRECTORY = PROJECT_ROOT / "build" / "properdocs"
API_BUILD_DIRECTORY = BUILD_DIRECTORY / "doc" / "api" / "current"
API_PUBLIC_PATH = Path("reference") / "api" / "main"

_serve_active = False
_last_source_fingerprint: tuple[tuple[str, int, int], ...] | None = None


def _source_files() -> Iterable[Path]:
    for root in (PROJECT_ROOT / "src", PROJECT_ROOT / "api-docs"):
        if root.is_dir():
            yield from (path for path in root.rglob("*") if path.is_file())

    cmake = PROJECT_ROOT / "CMakeLists.txt"
    if cmake.is_file():
        yield cmake

    modules = PROJECT_ROOT / "cmake" / "besa"
    if modules.is_dir():
        yield from (path for path in modules.rglob("*.cmake") if path.is_file())


def _source_fingerprint() -> tuple[tuple[str, int, int], ...]:
    values: list[tuple[str, int, int]] = []
    for path in _source_files():
        stat = path.stat()
        values.append((str(path.relative_to(PROJECT_ROOT)), stat.st_mtime_ns, stat.st_size))
    return tuple(sorted(values))


def _build_current_api() -> None:
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
    subprocess.run(
        ["cmake", "--build", str(BUILD_DIRECTORY), "--target", "user.docs.api"],
        cwd=PROJECT_ROOT,
        check=True,
    )


def _ensure_current_api() -> None:
    global _last_source_fingerprint

    fingerprint = _source_fingerprint()
    if API_BUILD_DIRECTORY.is_dir() and fingerprint == _last_source_fingerprint:
        return

    _build_current_api()
    _last_source_fingerprint = fingerprint


def _publish_current_api(site_directory: Path) -> None:
    if not API_BUILD_DIRECTORY.is_dir():
        return

    destination = site_directory / API_PUBLIC_PATH
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(API_BUILD_DIRECTORY, destination)

    (destination.parent / "versions.json").write_text(
        json.dumps(
            {"default": "main", "versions": [{"name": "main", "url": "main/"}]},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (site_directory / ".nojekyll").touch()


def on_startup(*, command: str, dirty: bool = False, **_kwargs) -> None:
    """Enable the API hook only for the long-running development server."""

    del dirty
    global _serve_active
    _serve_active = command == "serve"


def on_pre_build(**_kwargs) -> None:
    if _serve_active:
        _ensure_current_api()


def on_post_build(config, **_kwargs) -> None:
    if _serve_active:
        _publish_current_api(Path(config["site_dir"]).resolve())
