# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
"""Command-line interface for cpdoc."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from .build import build_current, build_versions
from .config import load_config


def _path(value: str) -> Path:
    return Path(value).expanduser()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cpdoc", description="Generate semantic API documentation")
    parser.add_argument("--config", type=_path, default=Path("cpdoc.yml"))
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="build the current checkout")
    build.add_argument("--output-directory", type=_path)
    build.add_argument("--work-directory", type=_path)
    build.add_argument("--version", default="main")
    build.add_argument("--variant", action="append", default=[])

    versions = commands.add_parser("versions", help="build selected Git refs")
    versions.add_argument("--output-directory", type=_path)
    versions.add_argument("--work-directory", type=_path)
    versions.add_argument("--select")
    versions.add_argument("--variant", action="append", default=[])

    arguments = parser.parse_args(argv)
    try:
        config = load_config(arguments.config)
        if arguments.variant:
            config = replace(config, variants=tuple(arguments.variant))
        if arguments.command == "build":
            build_current(
                config,
                output_directory=arguments.output_directory,
                work_directory=arguments.work_directory,
                version=arguments.version,
            )
        else:
            build_versions(
                config,
                output_directory=arguments.output_directory,
                work_directory=arguments.work_directory,
                selector=arguments.select,
            )
    except RuntimeError as error:
        parser.exit(2, f"cpdoc: {error}\n")
    return 0
