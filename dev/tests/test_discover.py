# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------
import pathlib as _pathlib

import pytest as _pytest

import besa_dev.compilers as _compilers
import besa_dev.discover as _discover

CONFIG = _pathlib.Path(__file__).parents[1] / "etc" / "compilers.json"


def fake(pages: dict[str, object]) -> _discover.Fetch:
    def fetch(url: str) -> object:
        return pages[url]

    return fetch


def test_docker_hub_follows_pagination_and_filters_tags() -> None:
    first = f"{_discover.DOCKER_HUB}/library/gcc/tags?page_size=100"
    second = "https://hub.docker.com/next-page"
    fetch = fake(
        {
            first: {
                "results": [{"name": "17"}, {"name": "latest"}],
                "next": second,
            },
            second: {
                "results": [{"name": "16.2.0"}, {"name": "16"}],
                "next": None,
            },
        }
    )
    majors = _discover.docker_hub_tag_majors("library/gcc", "^(\\d+)$", fetch)
    assert majors == {16, 17}


def test_github_skips_prereleases_and_drafts() -> None:
    base = f"{_discover.GITHUB_API}/llvm/llvm-project/releases?per_page=100"
    fetch = fake(
        {
            f"{base}&page=1": [
                {"tag_name": "llvmorg-24.1.0-rc1", "prerelease": True},
                {"tag_name": "llvmorg-23.1.0", "prerelease": False},
                {"tag_name": "llvmorg-25.1.0", "draft": True},
            ],
            f"{base}&page=2": [{"tag_name": "llvmorg-22.1.8"}],
            f"{base}&page=3": [],
        }
    )
    pattern = "^llvmorg-(\\d+)\\.\\d+\\.\\d+$"
    majors = _discover.github_release_majors(
        "llvm/llvm-project", pattern, fetch
    )
    assert majors == {22, 23}


def test_unexpected_response_is_reported() -> None:
    url = f"{_discover.DOCKER_HUB}/library/gcc/tags?page_size=100"
    with _pytest.raises(_discover.DiscoveryError):
        _discover.docker_hub_tag_majors(
            "library/gcc", "^(\\d+)$", fake({url: {"detail": "throttled"}})
        )


def test_synchronize_adds_new_versions_and_keeps_flags() -> None:
    config = _compilers.load(CONFIG)
    flagged = tuple(
        _compilers.Compiler(c.family, c.version, c.family == "clang")
        for c in config.compilers
    )
    config = _compilers.Config(config.families, flagged)
    newest = max(c.version for c in config.compilers if c.family == "gcc")
    updated = _discover.synchronize(config, {"gcc": {1, newest + 1}})
    added, removed = _discover.difference(config, updated)
    assert [(c.family, c.version) for c in added] == [("gcc", newest + 1)]
    assert removed == []
    assert updated.compilers[0].version == newest + 1
    assert all(c.experimental for c in updated.compilers if c.family == "clang")


def test_synchronize_retires_versions_below_a_raised_minimum() -> None:
    config = _compilers.load(CONFIG)
    gcc = _compilers.family(config, "gcc")
    raised = _compilers.Family(
        name=gcc.name,
        minimum=gcc.minimum + 1,
        discovery=gcc.discovery,
        image=gcc.image,
        setup=gcc.setup,
        cc=gcc.cc,
        cxx=gcc.cxx,
        path=gcc.path,
    )
    families = tuple(raised if f.name == "gcc" else f for f in config.families)
    config = _compilers.Config(families, config.compilers)
    updated = _discover.synchronize(config, {})
    _, removed = _discover.difference(config, updated)
    assert [(c.family, c.version) for c in removed] == [("gcc", gcc.minimum)]


def test_synchronize_rejects_unknown_family() -> None:
    config = _compilers.load(CONFIG)
    with _pytest.raises(_discover.DiscoveryError, match="unknown family"):
        _discover.synchronize(config, {"icc": {2025}})
