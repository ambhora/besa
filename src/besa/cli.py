# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
"""Command-line interface for BESA.

The command line deliberately has a very small surface area.  BESA does not parse or rewrite a
project's CMake files.  For C++ it only creates a simple project skeleton and installs the versioned
BESA CMake implementation into a project-owned directory.  Updating that directory is therefore a
safe, explicit operation which leaves the project's build description untouched.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from .metadata import __version__

_PROJECT_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_DEFAULT_CPP_MODULE_PATH = Path("cmake/besa")
_MANAGED_MARKER = ".besa-cmake-module"
_DEFAULT_SPDX_LICENSE = "Apache-2.0"
_DEFAULT_CPP_DIRECTORY = "main"
_EDITOR_IGNORE_ENTRIES = (".nvimrc", ".ycm_extra_conf.py")


def share_directory() -> Path:
    """Return the directory containing BESA's installed shared resources.

    ``BESA_SHARE_DIR`` is an explicit override for tests and package-manager integration.  When
    running from an editable/source-tree installation, prefer the repository's live ``share/besa``
    directory so changes to templates and CMake modules are visible immediately.  A regular wheel
    installation falls back to the shared data installed below ``sys.prefix/share/besa``.
    """

    override = os.environ.get("BESA_SHARE_DIR")
    if override:
        candidate = Path(override).expanduser().resolve()
        if candidate.is_dir():
            return candidate
        raise RuntimeError(f"BESA_SHARE_DIR does not exist: {candidate}")

    source_tree = Path(__file__).resolve().parents[2] / "share" / "besa"
    if source_tree.is_dir():
        return source_tree

    installed = Path(sys.prefix) / "share" / "besa"
    if installed.is_dir():
        return installed

    raise RuntimeError("Could not locate BESA shared data")


def _validate_project_name(name: str) -> None:
    if not _PROJECT_NAME.fullmatch(name):
        raise ValueError(
            f"Invalid project name '{name}'. Project names must match [a-z][a-z0-9_]*."
        )


def _render_tree(
    destination: Path, project_name: str, spdx_license_identifier: str = _DEFAULT_SPDX_LICENSE
) -> None:
    """Render the intentionally tiny template language used by BESA.

    Templates use the literal tokens ``vorlage`` and ``Vorlage`` for the project name and its
    class-name form, ``BESA_PROJECT_UPPER`` where an uppercase project token is required, the default
    SPDX identifier for generated-file license headers, ``BESA_PROJECT_LICENSE`` for places where
    the project license is displayed as content, and the suffix ``.in`` to mark files which become
    active manifests after generation. Keeping the rendering
    model this small is intentional: BESA must never need to understand CMake, TOML, or
    source-language syntax merely to create a project.
    """

    for path in destination.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        project_class_name = project_name.title().replace("_", "")
        rendered = (
            text.replace("BESA_PROJECT_UPPER", project_name.upper())
            .replace("vorlage", project_name)
            .replace("Vorlage", project_class_name)
        )
        rendered = rendered.replace(
            f"SPDX-License-Identifier: {_DEFAULT_SPDX_LICENSE}",
            f"SPDX-License-Identifier: {spdx_license_identifier}",
        )
        rendered = rendered.replace("BESA_PROJECT_LICENSE", spdx_license_identifier)
        path.write_text(rendered, encoding="utf-8")

    # Rename deepest paths first so include/package directories are safely renamed before parents.
    for path in sorted(destination.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if "vorlage" in path.name:
            path.rename(path.with_name(path.name.replace("vorlage", project_name)))

    for template_input in sorted(destination.rglob("*.in")):
        template_input.rename(template_input.with_suffix(""))


def _safe_relative_module_path(module_path: str | Path) -> Path:
    path = Path(module_path)
    if path.is_absolute():
        raise ValueError("--module-path must be relative to --project")
    if not path.parts or any(part == ".." for part in path.parts):
        raise ValueError("--module-path must stay inside the project directory")
    return path


def cpp_update(project: Path | str, module_path: Path | str = _DEFAULT_CPP_MODULE_PATH) -> Path:
    """Install the current BESA CMake modules into a C++ project.

    The update is directory-granular: a complete temporary copy is prepared first and then moved
    into place.  Existing directories are replaced only when they carry BESA's management marker,
    preventing an accidental ``--module-path`` typo from deleting unrelated project data.
    """

    project_root = Path(project).expanduser().resolve()
    if not project_root.is_dir():
        raise ValueError(f"Project directory does not exist: {project_root}")

    relative = _safe_relative_module_path(module_path)
    destination = project_root / relative
    source = share_directory() / "cpp" / "cmake"
    if not source.is_dir():
        raise RuntimeError(f"BESA CMake module directory was not found: {source}")

    if destination.exists():
        marker = destination / _MANAGED_MARKER
        if not marker.is_file():
            raise RuntimeError(
                f"Refusing to replace non-BESA directory: {destination}. "
                f"Expected management marker {marker.name}."
            )

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".besa-update-", dir=destination.parent) as temporary:
        staged = Path(temporary) / "besa"
        shutil.copytree(source, staged)
        (staged / _MANAGED_MARKER).write_text(
            f"BESA CMake module\nversion={__version__}\n", encoding="utf-8"
        )

        if destination.exists():
            shutil.rmtree(destination)
        shutil.move(str(staged), str(destination))

    return destination


def _validate_directory_name(directory: str) -> None:
    path = Path(directory)
    if (
        not directory
        or path.is_absolute()
        or len(path.parts) != 1
        or path.parts[0] in {".", ".."}
    ):
        raise ValueError("Directory name must be a single relative path component")


def _install_nvim_ycm_config(destination: Path) -> None:
    """Install local Neovim/YCM helpers and keep them out of version control."""

    source = share_directory() / "cpp" / "editor" / "nvim-ycm"
    if not source.is_dir():
        raise RuntimeError(f"BESA Neovim/YCM resources were not found: {source}")

    shutil.copy2(source / "nvimrc", destination / ".nvimrc")
    shutil.copy2(source / "ycm_extra_conf.py", destination / ".ycm_extra_conf.py")

    gitignore = destination / ".gitignore"
    text = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
    if text and not text.endswith("\n"):
        text += "\n"
    missing = [entry for entry in _EDITOR_IGNORE_ENTRIES if entry not in text.splitlines()]
    if missing:
        if text and not text.endswith("\n\n"):
            text += "\n"
        text += "# Local editor configuration generated by BESA.\n"
        text += "\n".join(missing) + "\n"
        gitignore.write_text(text, encoding="utf-8")


def cpp_generate(
    path: Path | str,
    name: str,
    license_identifier: str = _DEFAULT_SPDX_LICENSE,
    directory: str = _DEFAULT_CPP_DIRECTORY,
    nvim_ycm: bool = False,
) -> Path:
    """Create a self-contained C++ project under ``path/directory``."""

    license_identifier = license_identifier.strip()
    if not license_identifier:
        raise ValueError("SPDX license identifier must not be empty")

    _validate_project_name(name)
    _validate_directory_name(directory)
    parent = Path(path).expanduser().resolve()
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / directory
    if destination.exists():
        raise FileExistsError(f"Destination already exists: {destination}")

    template = share_directory() / "cpp" / "vorlage"
    if not template.is_dir():
        raise RuntimeError(f"BESA C++ template was not found: {template}")

    shutil.copytree(template, destination)
    if nvim_ycm:
        _install_nvim_ycm_config(destination)
    _render_tree(destination, name, license_identifier)
    cpp_update(destination)
    return destination


def python_generate() -> Path:
    """Generate the Python template in the current directory.

    The current directory name is the project name.  This keeps the first Python command deliberately
    minimal while still allowing BESA to grow a richer Python interface later without changing the
    C++ command surface.
    """

    destination = Path.cwd().resolve()
    name = destination.name
    _validate_project_name(name)

    template = share_directory() / "python" / "vorlage"
    if not template.is_dir():
        raise RuntimeError(f"BESA Python template was not found: {template}")

    conflicts = [item.name for item in template.iterdir() if (destination / item.name).exists()]
    # pyproject.toml.in is rendered to pyproject.toml, so check the rendered path explicitly.
    if (destination / "pyproject.toml").exists():
        conflicts.append("pyproject.toml")
    if conflicts:
        raise FileExistsError(
            "Python generation would overwrite existing paths: " + ", ".join(sorted(set(conflicts)))
        )

    for item in template.iterdir():
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)

    _render_tree(destination, name)
    return destination


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="besa", description="BESA project development tooling")
    commands = parser.add_subparsers(dest="command")

    cpp = commands.add_parser("cpp", help="C++ project operations")
    cpp_commands = cpp.add_subparsers(dest="cpp_command")

    cpp_generate_parser = cpp_commands.add_parser(
        "generate", help="Generate a self-contained C++ project"
    )
    cpp_generate_parser.add_argument(
        "--path", required=True, help="Directory under which the generated checkout is created"
    )
    cpp_generate_parser.add_argument("--name", required=True, help="Project name")
    cpp_generate_parser.add_argument(
        "--directory",
        default=_DEFAULT_CPP_DIRECTORY,
        help=f"Directory created below --path (default: {_DEFAULT_CPP_DIRECTORY})",
    )
    cpp_generate_parser.add_argument(
        "--license",
        dest="license_identifier",
        default=_DEFAULT_SPDX_LICENSE,
        help=f"SPDX license identifier for generated project files (default: {_DEFAULT_SPDX_LICENSE})",
    )
    cpp_generate_parser.add_argument(
        "--nvim-ycm",
        action="store_true",
        help="Install gitignored .nvimrc and .ycm_extra_conf.py local editor configuration",
    )

    cpp_update_parser = cpp_commands.add_parser(
        "update", help="Install or update the vendored BESA CMake module"
    )
    cpp_update_parser.add_argument("--project", required=True, help="Project root")
    cpp_update_parser.add_argument(
        "--module-path",
        default=str(_DEFAULT_CPP_MODULE_PATH),
        help="BESA module path relative to the project root (default: cmake/besa)",
    )

    python = commands.add_parser("python", help="Python project operations")
    python_commands = python.add_subparsers(dest="python_command")
    python_commands.add_parser(
        "generate", help="Generate a Python project in the current directory"
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Parent commands intentionally show help rather than producing argparse's "required subcommand"
    # error.  This makes the nested CLI discoverable from the terminal.
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "cpp" and args.cpp_command is None:
        next(action for action in parser._actions if isinstance(action, argparse._SubParsersAction)).choices[
            "cpp"
        ].print_help()
        return 0
    if args.command == "python" and args.python_command is None:
        next(action for action in parser._actions if isinstance(action, argparse._SubParsersAction)).choices[
            "python"
        ].print_help()
        return 0

    try:
        if args.command == "cpp" and args.cpp_command == "generate":
            destination = cpp_generate(
                args.path,
                args.name,
                license_identifier=args.license_identifier,
                directory=args.directory,
                nvim_ycm=args.nvim_ycm,
            )
            print(f"Created C++ project '{args.name}' at {destination}")
            return 0

        if args.command == "cpp" and args.cpp_command == "update":
            destination = cpp_update(args.project, args.module_path)
            print(f"Updated BESA CMake module at {destination}")
            return 0

        if args.command == "python" and args.python_command == "generate":
            destination = python_generate()
            print(f"Generated Python project '{destination.name}' in {destination}")
            return 0
    except (FileExistsError, RuntimeError, ValueError) as error:
        print(f"besa: {error}", file=sys.stderr)
        return 2

    parser.error("unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
