# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
"""Select BESA API refs and invoke sphinx-multiversion safely.

Version selection is deliberately resolved outside ``api-docs/conf.py``. sphinx-multiversion loads
``conf.py`` from every selected Git ref in a temporary exported tree while collecting metadata. A
configuration file must therefore not need access to the repository's ``.git`` directory merely to
be importable.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

from packaging.version import InvalidVersion, Version

_RANGE_PART = re.compile(r"^(>=|<=|==|!=|>|<)\s*(.+)$")


def _properdocs_extra_value(project_root: Path, name: str) -> str | None:
    """Read one simple scalar from the top-level ``extra`` mapping without requiring PyYAML."""

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


def _selector(project_root: Path) -> str:
    return (
        os.environ.get("BESA_API_VERSIONS")
        or _properdocs_extra_value(project_root, "besa_api_versions")
        or "all"
    ).strip()


def _git_ref_names(project_root: Path, namespace: str) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "for-each-ref", "--format=%(refname:short)", f"refs/{namespace}/"],
            cwd=project_root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError(
            f"BESA_API_VERSIONS={_selector(project_root)!r} requires a readable Git repository"
        ) from error
    return [line for line in result.stdout.splitlines() if line]


def _versioned_tags(project_root: Path) -> list[tuple[Version, str]]:
    result: list[tuple[Version, str]] = []
    for tag in _git_ref_names(project_root, "tags"):
        try:
            parsed = Version(tag)
        except InvalidVersion:
            continue
        result.append((parsed, tag))
    return sorted(result, key=lambda item: (item[0], item[1]))


def _exact_ref_pattern(names: list[str]) -> str:
    if not names:
        return r"(?!)"
    return r"^(?:" + "|".join(re.escape(name) for name in sorted(set(names))) + r")$"


def _version_in_range(version_value: Version, expression: str) -> bool:
    comparators = [part.strip() for part in expression.split(",") if part.strip()]
    if not comparators:
        raise RuntimeError("BESA API version range must contain at least one comparator")

    for comparator in comparators:
        match = _RANGE_PART.fullmatch(comparator)
        if match is None:
            raise RuntimeError(
                f"invalid BESA API version range comparator {comparator!r}; "
                "use forms such as >=0.2,<0.6"
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


def selected_refs(project_root: Path, selector: str) -> tuple[str, str]:
    """Return exact sphinx-multiversion branch/tag regexes for one BESA selector."""

    selector = selector.strip()
    branches = ["main"]

    if selector == "all":
        return _exact_ref_pattern(branches), r"^.*$"

    if selector.startswith("latest:"):
        raw_count = selector.removeprefix("latest:").strip()
        try:
            count = int(raw_count)
        except ValueError as error:
            raise RuntimeError(f"invalid BESA API latest selector {selector!r}") from error
        if count < 1:
            raise RuntimeError("BESA API latest selector must request at least one version")
        tags = [tag for _version, tag in _versioned_tags(project_root)[-count:]]
        return _exact_ref_pattern(branches), _exact_ref_pattern(tags)

    if selector.startswith("range:"):
        expression = selector.removeprefix("range:").strip()
        tags = [
            tag
            for parsed, tag in _versioned_tags(project_root)
            if _version_in_range(parsed, expression)
        ]
        return _exact_ref_pattern(branches), _exact_ref_pattern(tags)

    if selector.startswith("refs:"):
        requested = [
            item.strip()
            for item in selector.removeprefix("refs:").split(",")
            if item.strip()
        ]
        if not requested:
            raise RuntimeError("BESA API refs selector must contain at least one ref")
        branch_names = set(_git_ref_names(project_root, "heads"))
        tag_names = set(_git_ref_names(project_root, "tags"))
        unknown = [name for name in requested if name not in branch_names and name not in tag_names]
        if unknown:
            raise RuntimeError("unknown BESA API Git refs: " + ", ".join(unknown))
        branches.extend(name for name in requested if name in branch_names)
        tags = [name for name in requested if name in tag_names]
        return _exact_ref_pattern(branches), _exact_ref_pattern(tags)

    raise RuntimeError(
        f"unsupported BESA_API_VERSIONS selector {selector!r}; expected all, latest:N, "
        "range:<comparators>, or refs:<ref,...>"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sphinx-multiversion", required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--source-directory", required=True)
    parser.add_argument("--output-directory", required=True)
    parser.add_argument("sphinx_arguments", nargs=argparse.REMAINDER)
    arguments = parser.parse_args(argv)

    project_root = arguments.project_root.resolve()
    selector = _selector(project_root)
    branch_pattern, tag_pattern = selected_refs(project_root, selector)

    sphinx_arguments = list(arguments.sphinx_arguments)
    if sphinx_arguments[:1] == ["--"]:
        sphinx_arguments = sphinx_arguments[1:]

    # Old Git refs may contain a conf.py from the first implementation of BESA_API_VERSIONS, which
    # tried to inspect Git while sphinx-multiversion was loading that config from a temporary exported
    # tree. Force that historical code down its non-Git ``all`` path.
    #
    # Pass the exact SMV ref filters through the environment rather than ``-D``. sphinx-multiversion
    # reads its config before its Sphinx extension registers the smv_* keys; at that point ``-D``
    # overrides are unknown and are ignored. The current BESA conf.py reads these two internal values
    # during normal Python config execution, before SMV asks for Git refs.
    environment = os.environ.copy()
    environment["BESA_API_VERSIONS"] = "all"
    environment["BESA_SMV_BRANCH_WHITELIST"] = branch_pattern
    environment["BESA_SMV_TAG_WHITELIST"] = tag_pattern

    command = [
        arguments.sphinx_multiversion,
        *sphinx_arguments,
        arguments.source_directory,
        arguments.output_directory,
    ]
    subprocess.run(command, cwd=project_root, check=True, env=environment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
