# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from cpdoc.config import load_config


def test_cpdoc_config_resolves_paths_relative_to_config(tmp_path: Path) -> None:
    config_file = tmp_path / "cpdoc.yml"
    (tmp_path / "api-docs").mkdir()
    (tmp_path / "api-docs" / "index.md").write_text("# API\n", encoding="utf-8")
    config_file.write_text(
        """schema: 1
project:
  root: .
  provider: besa
  language: cpp
content:
  index: api-docs/index.md
output:
  current: build/api/current
  versions: build/api/versions
  work: build/work/cpdoc
versions:
  select: latest:3
  default: main
""",
        encoding="utf-8",
    )
    config = load_config(config_file)
    assert config.project_root == tmp_path.resolve()
    assert config.content_index == (tmp_path / "api-docs" / "index.md").resolve()
    assert config.output_current == (tmp_path / "build/api/current").resolve()
    assert config.versions_selector == "latest:3"
