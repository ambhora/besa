# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from properdocs_cpdoc.core import publish_api, resolve_api_references


def test_semantic_api_links_resolve_against_mount() -> None:
    rendered = resolve_api_references(
        "See @apidocs::dice::meta::build and @apidocs[v1.2]::dice.solve.",
        page_dest_uri="reference/index.html",
        mount="reference/api",
        default_version="main",
    )
    assert "(api/main/_symbols/dice/meta/build/)" in rendered
    assert "(api/v1.2/_symbols/dice/solve/)" in rendered


def test_publish_replaces_api_subtree(tmp_path: Path) -> None:
    source = tmp_path / "cpdoc"
    (source / "main").mkdir(parents=True)
    (source / "main" / "index.html").write_text("new", encoding="utf-8")
    site = tmp_path / "site"
    stale = site / "reference" / "api" / "old"
    stale.mkdir(parents=True)
    (stale / "index.html").write_text("old", encoding="utf-8")
    destination = publish_api(source, site, "reference/api")
    assert (destination / "main" / "index.html").read_text(encoding="utf-8") == "new"
    assert not (destination / "old").exists()
    assert (site / ".nojekyll").is_file()
