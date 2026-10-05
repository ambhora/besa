# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------
from pathlib import Path

import pytest

from besa.vendor import VendorError, vendor


def _payload(path: Path, marker: str) -> Path:
    path.mkdir(parents=True)
    (path / "besaConfig.cmake").write_text(marker)
    (path / "module.cmake").write_text(marker)
    return path


def test_vendor_copies_cmake_payload(tmp_path: Path):
    source = _payload(tmp_path / "installed", "new")
    project = tmp_path / "project"

    destination = vendor(project, source)

    assert destination == project / "cmake" / "besa"
    assert (destination / "besaConfig.cmake").read_text() == "new"
    assert (destination / "module.cmake").read_text() == "new"


def test_vendor_replaces_previous_payload(tmp_path: Path):
    source = _payload(tmp_path / "installed", "new")
    destination = tmp_path / "project" / "cmake" / "besa"
    destination.mkdir(parents=True)
    (destination / "obsolete.cmake").write_text("old")

    vendor(tmp_path / "project", source)

    assert not (destination / "obsolete.cmake").exists()
    assert (destination / "besaConfig.cmake").read_text() == "new"


def test_vendor_requires_besa_config(tmp_path: Path):
    source = tmp_path / "installed"
    source.mkdir()

    with pytest.raises(VendorError, match="BESA CMake data not found"):
        vendor(tmp_path / "project", source)
