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
            "cpdoc version selection requires a readable Git repository"
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
        raise RuntimeError("cpdoc version range must contain at least one comparator")
    for comparator in comparators:
        match = _RANGE_PART.fullmatch(comparator)
        if match is None:
            raise RuntimeError(
                f"invalid cpdoc version range comparator {comparator!r}; use forms such as >=0.2,<0.6"
            )
        operator, raw_version = match.groups()
        try:
            boundary = Version(raw_version.strip())
        except InvalidVersion as error:
            raise RuntimeError(f"invalid cpdoc version {raw_version!r} in range") from error
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
            raise RuntimeError(f"invalid cpdoc latest selector {value!r}") from error
        if count < 1:
            raise RuntimeError("cpdoc latest selector must request at least one version")
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
            raise RuntimeError("cpdoc refs selector must contain at least one ref")
        known = set(_git_ref_names(project_root, "heads")) | set(_git_ref_names(project_root, "tags"))
        unknown = [name for name in requested if name not in known]
        if unknown:
            raise RuntimeError("unknown cpdoc Git refs: " + ", ".join(unknown))
        refs.extend(requested)
        return list(dict.fromkeys(refs))
    raise RuntimeError(
        f"unsupported cpdoc version selector {value!r}; expected all, latest:N, "
        "range:<comparators>, or refs:<ref,...>"
    )
