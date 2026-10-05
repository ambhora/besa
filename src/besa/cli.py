# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------
"""Command-line interface for BESA."""

import argparse
from pathlib import Path

from besa.vendor import VendorError, vendor


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="besa")
    commands = result.add_subparsers(dest="command", required=True)
    vendor_parser = commands.add_parser(
        "vendor", help="vendor BESA's CMake files into a C++ project"
    )
    vendor_parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        type=Path,
        help="project directory (default: current directory)",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        destination = vendor(args.directory)
    except VendorError as error:
        parser().error(str(error))
    print(destination)
    return 0
