# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
"""Git-ref selection for BESA's versioned API site."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from packaging.version import InvalidVersion, Version

_RANGE_PART = re.compile(r"^(>=|<=|==|!=|>|<)\s*(.+)$")


def properdocs_extra_value(project_root: Path, name: str) -> str | None:
    config = project_root / "properdocs.yml"
    if not config.is_file():
        return None
    in_extra = False
    for line in config.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            in_extra = stripped == "extra:"
            continue
        if not in_extra:
            continue
        match = re.match(rf"\s+{re.escape(name)}\s*:\s*(.*?)\s*$", line)
        if match is None:
            continue
        value = match.group(1).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        return value or None
    return None


def selector(project_root: Path) -> str:
    return (
        os.environ.get("BESA_API_VERSIONS")
        or properdocs_extra_value(project_root, "besa_api_versions")
        or "all"
    ).strip()


def _git_ref_names(project_root: Path, namespace: str) -> list[str]:
    result = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname:short)", f"refs/{namespace}/"],
        cwd=project_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"BESA_API_VERSIONS={selector(project_root)!r} requires a readable Git repository"
        )
    return [line for line in result.stdout.splitlines() if line]


def _versioned_tags(project_root: Path) -> list[tuple[Version, str]]:
    values: list[tuple[Version, str]] = []
    for tag in _git_ref_names(project_root, "tags"):
        try:
            parsed = Version(tag)
        except InvalidVersion:
            continue
        values.append((parsed, tag))
    return sorted(values, key=lambda item: (item[0], item[1]))


def _version_in_range(version_value: Version, expression: str) -> bool:
    comparators = [part.strip() for part in expression.split(",") if part.strip()]
    if not comparators:
        raise RuntimeError("BESA API version range must contain at least one comparator")
    for comparator in comparators:
        match = _RANGE_PART.fullmatch(comparator)
        if match is None:
            raise RuntimeError(
                f"invalid BESA API version range comparator {comparator!r}; use forms such as >=0.2,<0.6"
            )
        operator, raw_version = match.groups()
        try:
            boundary = Version(raw_version.strip())
        except InvalidVersion as error:
            raise RuntimeError(f"invalid BESA API version {raw_version!r} in range") from error
        relation = {
            ">=": version_value >= boundary,
            "<=": version_value <= boundary,
            "==": version_value == boundary,
            "!=": version_value != boundary,
            ">": version_value > boundary,
            "<": version_value < boundary,
        }[operator]
        if not relation:
            return False
    return True


def selected_ref_names(project_root: Path, value: str) -> list[str]:
    value = value.strip()
    refs = ["main"]
    if value == "all":
        refs.extend(tag for _version, tag in reversed(_versioned_tags(project_root)))
        return list(dict.fromkeys(refs))
    if value.startswith("latest:"):
        try:
            count = int(value.removeprefix("latest:").strip())
        except ValueError as error:
            raise RuntimeError(f"invalid BESA API latest selector {value!r}") from error
        if count < 1:
            raise RuntimeError("BESA API latest selector must request at least one version")
        refs.extend(tag for _version, tag in reversed(_versioned_tags(project_root)[-count:]))
        return list(dict.fromkeys(refs))
    if value.startswith("range:"):
        expression = value.removeprefix("range:").strip()
        refs.extend(
            tag
            for parsed, tag in reversed(_versioned_tags(project_root))
            if _version_in_range(parsed, expression)
        )
        return list(dict.fromkeys(refs))
    if value.startswith("refs:"):
        requested = [item.strip() for item in value.removeprefix("refs:").split(",") if item.strip()]
        if not requested:
            raise RuntimeError("BESA API refs selector must contain at least one ref")
        known = set(_git_ref_names(project_root, "heads")) | set(_git_ref_names(project_root, "tags"))
        unknown = [name for name in requested if name not in known]
        if unknown:
            raise RuntimeError("unknown BESA API Git refs: " + ", ".join(unknown))
        refs.extend(requested)
        return list(dict.fromkeys(refs))
    raise RuntimeError(
        f"unsupported BESA_API_VERSIONS selector {value!r}; expected all, latest:N, "
        "range:<comparators>, or refs:<ref,...>"
    )
