# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------
"""Vendor the CMake part of an installed BESA distribution into a project."""

import os
import shutil
import sysconfig
import tempfile
from pathlib import Path


class VendorError(Exception):
    """BESA's installed CMake payload cannot be vendored."""


def cmake_share() -> Path:
    """Return the CMake payload installed by Hatch as shared wheel data."""
    return Path(sysconfig.get_path("data")) / "share" / "besa" / "cmake"


def vendor(project: Path, source: Path | None = None) -> Path:
    """Replace ``project/cmake/besa`` with this BESA installation's payload."""
    source = source or cmake_share()
    if not (source / "besaConfig.cmake").is_file():
        raise VendorError(f"BESA CMake data not found at {source}")

    cmake = project.resolve() / "cmake"
    destination = cmake / "besa"
    cmake.mkdir(parents=True, exist_ok=True)

    temporary = Path(tempfile.mkdtemp(prefix=".besa-", dir=cmake))
    backup = cmake / ".besa-backup"
    try:
        payload = temporary / "besa"
        shutil.copytree(source, payload)
        if backup.exists():
            shutil.rmtree(backup)
        if destination.exists():
            os.replace(destination, backup)
        os.replace(payload, destination)
        if backup.exists():
            shutil.rmtree(backup)
    except Exception:
        if backup.exists() and not destination.exists():
            os.replace(backup, destination)
        raise
    finally:
        shutil.rmtree(temporary, ignore_errors=True)

    return destination
