# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------
import pathlib as _pathlib
import shutil as _shutil

import besa_dev.cli as _cli
import besa_dev.compilers as _compilers
import besa_dev.discover as _discover

CONFIG = _pathlib.Path(__file__).parents[1] / "etc" / "compilers.json"


def test_discover_write_updates_configuration(tmp_path, monkeypatch, capsys):
    path = tmp_path / "compilers.json"
    _shutil.copy(CONFIG, path)
    config = _compilers.load(path)
    newest = {
        family.name: max(
            c.version for c in config.compilers if c.family == family.name
        )
        for family in config.families
    }

    def available(family, fetch):
        return {newest[family.name] + 1}

    monkeypatch.setattr(_discover, "available", available)
    assert _cli.command_discover(config, path, True) == 0
    output = capsys.readouterr().out
    assert f"add     gcc-{newest['gcc'] + 1}" in output
    updated = _compilers.load(path)
    assert len(updated.compilers) == len(config.compilers) + 2
    assert _compilers.dump(updated) == path.read_text(encoding="utf-8")

    assert _cli.command_discover(updated, path, True) == 0
    assert "up to date" in capsys.readouterr().out


def test_find_root_walks_up(tmp_path) -> None:
    (tmp_path / "dev" / "etc").mkdir(parents=True)
    _shutil.copy(CONFIG, tmp_path / _cli.CONFIG_PATH)
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert _cli.find_root(nested) == tmp_path
