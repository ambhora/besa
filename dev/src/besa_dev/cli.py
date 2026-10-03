# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------
"""Command-line interface of besa-dev.

Subcommands:

``list``
    Show the configured compilers.
``matrix``
    Print the GitHub Actions matrix as JSON.
``run``
    Run the test suite for one compiler in its container.
``discover``
    Report compilers released upstream; ``--write`` updates compilers.json.
"""

import argparse as _argparse
import json as _json
import os as _os
import pathlib as _pathlib
import subprocess as _subprocess
import sys as _sys

import besa_dev.ci as _ci
import besa_dev.compilers as _compilers
import besa_dev.discover as _discover

CONFIG_PATH = _pathlib.Path("dev", "etc", "compilers.json")


def find_root(start: _pathlib.Path) -> _pathlib.Path:
    """The repository root: the nearest ancestor holding the configuration."""
    for candidate in (start, *start.parents):
        if (candidate / CONFIG_PATH).is_file():
            return candidate
    raise _compilers.ConfigError(
        f"no {CONFIG_PATH} found in {start} or its parents"
    )


def command_list(config: _compilers.Config) -> int:
    for compiler in config.compilers:
        flag = "  (experimental)" if compiler.experimental else ""
        image = _ci.image(config, compiler)
        print(f"{_ci.identifier(compiler):<12} {image}{flag}")
    return 0


def command_matrix(config: _compilers.Config) -> int:
    print(_json.dumps(_ci.matrix(config), separators=(",", ":")))
    return 0


def command_run(
    config: _compilers.Config,
    root: _pathlib.Path,
    name: str,
    engine: str,
    dry_run: bool,
) -> int:
    compiler = _ci.find(config, name)
    command = _ci.container_command(config, compiler, root, engine)
    print(_ci.render(command), file=_sys.stderr)
    if dry_run:
        return 0
    return _subprocess.run(command, check=False).returncode


def command_discover(
    config: _compilers.Config, path: _pathlib.Path, write: bool
) -> int:
    fetch = _discover.http_fetch(_os.environ.get("GITHUB_TOKEN"))
    versions = {
        family.name: _discover.available(family, fetch)
        for family in config.families
    }
    updated = _discover.synchronize(config, versions)
    added, removed = _discover.difference(config, updated)
    for compiler in added:
        print(f"add     {_ci.identifier(compiler)}")
    for compiler in removed:
        print(f"remove  {_ci.identifier(compiler)}")
    if not added and not removed:
        print("compilers are up to date")
    if write and updated != config:
        _compilers.save(updated, path)
        print(f"updated {path}")
    return 0


def parser() -> _argparse.ArgumentParser:
    result = _argparse.ArgumentParser(
        prog="besa-dev", description="BESA developer tooling"
    )
    result.add_argument(
        "--root",
        type=_pathlib.Path,
        help="repository root (default: found from the working directory)",
    )
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="show the configured compilers")
    commands.add_parser("matrix", help="print the GitHub Actions matrix")
    run = commands.add_parser("run", help="run the tests for one compiler")
    run.add_argument("compiler", help="compiler identifier, e.g. gcc-16")
    run.add_argument(
        "--engine", default="docker", help="container engine (default: docker)"
    )
    run.add_argument(
        "--dry-run", action="store_true", help="print the command only"
    )
    discover = commands.add_parser(
        "discover", help="find compilers released upstream"
    )
    discover.add_argument(
        "--write", action="store_true", help="update compilers.json"
    )
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        root = args.root or find_root(_pathlib.Path.cwd())
        path = root / CONFIG_PATH
        config = _compilers.load(path)
        if args.command == "list":
            return command_list(config)
        if args.command == "matrix":
            return command_matrix(config)
        if args.command == "run":
            return command_run(
                config, root, args.compiler, args.engine, args.dry_run
            )
        return command_discover(config, path, args.write)
    except (
        _compilers.ConfigError,
        _discover.DiscoveryError,
        _ci.UnknownCompilerError,
    ) as error:
        print(f"besa-dev: {error}", file=_sys.stderr)
        return 2
