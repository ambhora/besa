# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------
"""Discover released compiler versions and fold them into the configuration.

Each discovery kind reads one upstream listing and keeps the major versions
captured by the family's pattern:

``docker-hub-tags``
    Tags of a Docker Hub repository. Used where the tag is the installation
    source itself, so a version is only discovered once its image exists.
``github-releases``
    Published, non-prerelease releases of a GitHub repository.

Network access goes through a ``fetch`` callable taking a URL and returning
decoded JSON, so the discovery logic can be tested without a network.
"""

import json as _json
import re as _re
import typing as _typing
import urllib.parse as _parse
import urllib.request as _request

import besa_dev.compilers as _compilers

Fetch = _typing.Callable[[str], _typing.Any]

DOCKER_HUB = "https://hub.docker.com/v2/repositories"
GITHUB_API = "https://api.github.com/repos"
PAGE_SIZE = 100
MAXIMUM_PAGES = 50


class DiscoveryError(Exception):
    """An upstream listing could not be read or understood."""


def http_fetch(token: str | None) -> Fetch:
    """Return a fetch callable using urllib, authenticating to GitHub when a
    token is given."""

    def fetch(url: str) -> _typing.Any:
        headers = {"Accept": "application/json", "User-Agent": "besa-dev"}
        host = _parse.urlsplit(url).hostname
        if token and host == "api.github.com":
            headers["Authorization"] = f"Bearer {token}"
        request = _request.Request(url, headers=headers)
        try:
            with _request.urlopen(request, timeout=30) as response:
                return _json.load(response)
        except (OSError, ValueError) as error:
            raise DiscoveryError(f"cannot fetch {url}: {error}") from error

    return fetch


def _majors(names: _typing.Iterable[str], pattern: str) -> set[int]:
    compiled = _re.compile(pattern)
    result: set[int] = set()
    for name in names:
        match = compiled.fullmatch(name)
        if match:
            result.add(int(match.group(1)))
    return result


def docker_hub_tag_majors(
    repository: str, pattern: str, fetch: Fetch
) -> set[int]:
    """Major versions among the tags of a Docker Hub repository."""
    url: str | None = f"{DOCKER_HUB}/{repository}/tags?page_size={PAGE_SIZE}"
    names: list[str] = []
    for _ in range(MAXIMUM_PAGES):
        if url is None:
            break
        page = fetch(url)
        if not isinstance(page, dict) or not isinstance(
            page.get("results"), list
        ):
            raise DiscoveryError(f"unexpected Docker Hub response for {url}")
        names.extend(
            item["name"]
            for item in page["results"]
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        )
        url = page.get("next")
    return _majors(names, pattern)


def github_release_majors(
    repository: str, pattern: str, fetch: Fetch
) -> set[int]:
    """Major versions among the published releases of a GitHub repository."""
    names: list[str] = []
    for number in range(1, MAXIMUM_PAGES + 1):
        url = (
            f"{GITHUB_API}/{repository}/releases"
            f"?per_page={PAGE_SIZE}&page={number}"
        )
        page = fetch(url)
        if not isinstance(page, list):
            raise DiscoveryError(f"unexpected GitHub response for {url}")
        if not page:
            break
        names.extend(
            item["tag_name"]
            for item in page
            if isinstance(item, dict)
            and isinstance(item.get("tag_name"), str)
            and not item.get("draft")
            and not item.get("prerelease")
        )
    return _majors(names, pattern)


def available(family: _compilers.Family, fetch: Fetch) -> set[int]:
    """Major versions of a family that are available upstream."""
    discovery = family.discovery
    if discovery.kind == "docker-hub-tags":
        return docker_hub_tag_majors(
            discovery.repository, discovery.pattern, fetch
        )
    if discovery.kind == "github-releases":
        return github_release_majors(
            discovery.repository, discovery.pattern, fetch
        )
    raise DiscoveryError(f"unknown discovery kind '{discovery.kind}'")


def synchronize(
    config: _compilers.Config, versions: dict[str, set[int]]
) -> _compilers.Config:
    """Fold available versions into the configuration.

    Every available version at or above the family minimum is tested. Listed
    versions are kept with their flags even when upstream no longer lists
    them; only versions below the minimum are dropped. Raising a minimum in
    compilers.json therefore retires old compilers on the next run.
    """
    minimum = {family.name: family.minimum for family in config.families}
    kept = [
        compiler
        for compiler in config.compilers
        if compiler.version >= minimum[compiler.family]
    ]
    listed = {(compiler.family, compiler.version) for compiler in kept}
    for name, majors in versions.items():
        if name not in minimum:
            raise DiscoveryError(f"unknown family '{name}'")
        for version in sorted(majors):
            if version >= minimum[name] and (name, version) not in listed:
                kept.append(
                    _compilers.Compiler(
                        family=name, version=version, experimental=False
                    )
                )
    return _compilers.canonical(
        _compilers.Config(families=config.families, compilers=tuple(kept))
    )


def difference(
    old: _compilers.Config, new: _compilers.Config
) -> tuple[list[_compilers.Compiler], list[_compilers.Compiler]]:
    """Compilers added to and removed from old to obtain new."""
    before = {(c.family, c.version): c for c in old.compilers}
    after = {(c.family, c.version): c for c in new.compilers}
    added = [after[key] for key in after if key not in before]
    removed = [before[key] for key in before if key not in after]
    return added, removed
