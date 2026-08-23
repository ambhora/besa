# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
"""Sphinx configuration for BESA-generated C/C++ API documentation.

The API pipeline is intentionally layered:

    source comments -> Doxygen XML -> Breathe -> Exhale -> Sphinx HTML

Breathe exposes Doxygen XML to Sphinx. Exhale turns that complete API model into a navigable set of
namespace, class, file, function, and type pages instead of one monolithic ``doxygenindex`` page.

sphinx-multiversion builds this same configuration from every selected branch/tag. Its ``-c``
configuration directory remains the current checkout while ``app.srcdir`` points at the historical
checkout being rendered. Any checkout-specific path must therefore be derived from ``app.srcdir`` at
``builder-inited`` time, never from ``__file__``.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import posixpath
import re
import shlex
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath

CONFIG_DIRECTORY = Path(__file__).resolve().parent
# Sphinx loads extensions through normal Python imports. In multiversion builds the configuration
# directory is supplied with ``-c`` and is not guaranteed to be on ``sys.path``, so make the
# project-local compatibility extension next to this file importable explicitly.
sys.path.insert(0, str(CONFIG_DIRECTORY))

project = "vorlage"
author = ""


def _api_project_root(api_docs_directory: Path) -> Path:
    """Return the source checkout represented by one Sphinx source tree.

    Ordinary current-checkout builds stage ``api-docs/`` in the CMake build tree so Exhale can
    generate RST there without touching the source checkout.  sphinx-multiversion instead supplies
    checkout-specific source trees itself, so no override is set for those builds.
    """

    override = os.environ.get("BESA_API_PROJECT_SOURCE_DIRECTORY")
    if override:
        return Path(override).resolve()
    return api_docs_directory.parent.resolve()


def _cmake_project_version(project_root: Path) -> str:
    """Read ``project(... VERSION ...)`` from one concrete Git checkout."""

    cmake = (project_root / "CMakeLists.txt").read_text(encoding="utf-8")
    match = re.search(
        r"project\s*\([^)]*?\bVERSION\s+([0-9]+(?:\.[0-9]+){1,3})",
        cmake,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return match.group(1) if match else "0.0.0"


# These import-time values make direct ``sphinx-build`` configuration introspection useful. They are
# replaced from ``app.srcdir`` before an actual builder starts, which is essential for multiversion.
version = release = _cmake_project_version(_api_project_root(CONFIG_DIRECTORY))

extensions = [
    "besa_exhale_compat",
    "breathe",
    "exhale",
    "sphinx_multiversion",
]

templates_path = ["_templates"]
html_static_path = ["_static"]
html_css_files = ["css/besa-api.css"]
html_js_files = ["js/besa-api-version.js", "js/besa-api-presentation.js"]
exclude_patterns: list[str] = []

# Long C++ signatures use Sphinx's native logical-line formatting. Sphinx decides whether a
# parameter list is multiline from the rendered signature length, so short declarations remain
# compact and individual directives can still opt out with :single-line-parameter-list:.
cpp_maximum_signature_line_length = 122

html_theme = "pydata_sphinx_theme"
# Keep the navbar title version-independent. The selected API version is shown by the dedicated
# version selector, while Sphinx multiversion builds can otherwise inherit the current checkout
# release in the title even when rendering a historical ref.
html_title = f"{project} documentation"
html_short_title = html_title
html_theme_options = {
    "navbar_align": "right",
    # API entities belong in the persistent left section navigation, not in the site header.
    # PyData's default navbar-nav component renders every root toctree entry across the top.
    "navbar_center": [],
    # Keep all interactive header controls in one right-aligned group. Search is normally placed in
    # PyData's persistent header section, which leaves it next to the project title when the center
    # navbar is empty. Moving it into navbar_end makes Search, project docs, version, and theme mode
    # behave as one cluster.
    "navbar_persistent": [],
    "navbar_end": [
        "search-button-field",
        "project-links.html",
        "theme-switcher",
        "navbar-icon-links",
    ],
    "secondary_sidebar_items": ["page-toc"],
    "show_prev_next": False,
}

# Keep API navigation deliberately small. The left section navigation is a namespace index only;
# classes, functions, concepts, files, and other entities are reached from the namespace/member
# trees rather than repeated as one very long global sidebar.
html_sidebars = {
    # Keep only BESA's navigation component here. Older PyData Sphinx Theme releases do not
    # provide sidebar-collapse.html, while newer releases make collapsing an optional enhancement.
    "**": ["api-sidebar.html"],
}

# BESA mounts each Sphinx build below <ProperDocs root>/<API path>/<version>/. Templates use this
# depth plus pagename depth to construct deployment-prefix-independent links back to ProperDocs.
try:
    _besa_properdocs_root_depth = int(os.environ.get("BESA_PROPERDOCS_ROOT_DEPTH", "3"))
except ValueError as error:
    raise RuntimeError("BESA_PROPERDOCS_ROOT_DEPTH must be an integer") from error

html_context = {
    "besa_properdocs_root_depth": _besa_properdocs_root_depth,
}

# index.rst is rendered at <site>/<API path>/<version>/index.html. Keep the physical traversal out
# of checked-in RST so repository prefixes, custom domains, and alternate API mount points remain
# irrelevant to documentation authors.
_projectdocs_root_from_api_index = "../" * _besa_properdocs_root_depth
rst_prolog = (
    ".. |projectdocs| replace:: main project documentation\n"
    f".. _projectdocs: {_projectdocs_root_from_api_index}\n"
)

# sphinx-multiversion receives exact branch/tag filters from BESA's multiversion driver through
# environment variables. Using the environment rather than ``-D smv_*`` is intentional: SMV reads
# its configuration before its Sphinx extension registers those keys, so command-line overrides are
# otherwise reported as unknown and ignored. Historical exported refs need no Git access here.
smv_branch_whitelist = os.environ.get("BESA_SMV_BRANCH_WHITELIST", r"^main$")
smv_tag_whitelist = os.environ.get("BESA_SMV_TAG_WHITELIST", r"^.*$")
smv_outputdir_format = r"{ref.name}"

# Exhale automatically emits the complete API model represented by Doxygen XML. No class/function
# selection list is maintained by the project. Current-checkout builds stage this Sphinx source tree
# under the external documentation build directory before Exhale runs, so ``./generated`` is working
# state rather than source-tree output. Individual namespace/class/file pages remain separate.
exhale_args = {
    "containmentFolder": "./generated",
    "rootFileName": "library_root.rst",
    "rootFileTitle": f"{project} API",
    "doxygenStripFromPath": "..",
    "fullToctreeMaxDepth": 3,
    "contentsDirectives": True,
    "kindsWithContentsDirectives": ["namespace", "file"],
}


def _doxygen_base_directory() -> Path:
    return Path(
        os.environ.get(
            "BESA_DOXYGEN_BASE_DIRECTORY",
            CONFIG_DIRECTORY / "_build" / "doxygen",
        )
    ).resolve()


def _doxygen_output_for(project_root: Path) -> Path:
    """Return a stable, checkout-specific XML directory."""

    checkout_key = hashlib.sha256(str(project_root.resolve()).encode("utf-8")).hexdigest()[:16]
    return _doxygen_base_directory() / checkout_key


_default_doxygen_output = _doxygen_output_for(CONFIG_DIRECTORY.parent)
breathe_projects = {
    project: str(_default_doxygen_output / "xml"),
}
breathe_default_project = project


def _doxygen_quote(path: Path) -> str:
    """Return a Doxygen-safe quoted path."""

    return '"' + str(path).replace("\\", "/").replace('"', '\\"') + '"'


def _compile_database_cxx_standard(build_directory: Path) -> str | None:
    """Return an explicit C++ dialect option from one compilation database, if present."""

    database = build_directory / "compile_commands.json"
    if not database.is_file():
        return None

    try:
        entries = json.loads(database.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    for entry in entries:
        arguments = entry.get("arguments")
        if not arguments:
            command = entry.get("command")
            if not command:
                continue
            try:
                arguments = shlex.split(command)
            except ValueError:
                continue

        for argument in arguments:
            if argument.startswith("-std=") and "++" in argument:
                return argument
            if argument.startswith("/std:c++"):
                return "-std=" + argument.split(":", 1)[1]
    return None


def _cmake_default_cxx_standard(build_directory: Path) -> str | None:
    """Return the CMake-detected compiler-default C++ dialect for a configured build."""

    cmake_files = build_directory / "CMakeFiles"
    if not cmake_files.is_dir():
        return None

    for compiler_file in cmake_files.glob("*/CMakeCXXCompiler.cmake"):
        try:
            text = compiler_file.read_text(encoding="utf-8")
        except OSError:
            continue

        standard = re.search(
            r'set\(CMAKE_CXX_STANDARD_COMPUTED_DEFAULT\s+"?([^"\s\)]+)"?\)', text
        )
        if standard is None or not standard.group(1):
            continue

        extensions = re.search(
            r'set\(CMAKE_CXX_EXTENSIONS_COMPUTED_DEFAULT\s+"?([^"\s\)]+)"?\)', text
        )
        prefix = (
            "gnu++"
            if extensions and extensions.group(1).upper() in {"1", "ON", "TRUE", "YES"}
            else "c++"
        )
        return f"-std={prefix}{standard.group(1)}"
    return None


def _clang_resource_directory() -> Path:
    """Return the builtin-header resource directory for the libclang parser."""

    override = os.environ.get("BESA_CLANG_RESOURCE_DIRECTORY")
    if override:
        return Path(override).resolve()

    executable = os.environ.get("BESA_CLANG_EXECUTABLE") or shutil.which("clang")
    if executable is None:
        raise RuntimeError(
            "Clang-assisted Doxygen parsing requires a clang executable; set "
            "BESA_CLANG_EXECUTABLE or BESA_CLANG_RESOURCE_DIRECTORY"
        )

    result = subprocess.run(
        [executable, "-print-resource-dir"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    value = result.stdout.strip()
    if not value:
        raise RuntimeError(f"{executable} -print-resource-dir returned an empty path")
    return Path(value).resolve()


def _clang_options(build_directory: Path) -> list[str]:
    """Return parsing options needed when Doxygen invokes libclang on staged headers.

    ``compile_commands.json`` contains translation units, not the synthetic public headers Doxygen
    parses, so libclang cannot obtain a language dialect for those headers by database lookup. Use
    an explicit ``-std=`` from the database when available, otherwise mirror CMake's detected C++
    compiler default. libclang also needs Clang's resource directory to find builtin headers such
    as ``stddef.h`` and ``stdarg.h``.
    """

    standard = (
        _compile_database_cxx_standard(build_directory)
        or _cmake_default_cxx_standard(build_directory)
        or "-std=c++20"
    )
    resource = str(_clang_resource_directory()).replace("\\", "/")
    return [standard, f"-resource-dir={resource}"]


def _doxygen_list(values: list[str]) -> str:
    """Return Doxygen configuration-list syntax for command-line option strings."""

    return " ".join('"' + value.replace('"', '\\"') + '"' for value in values)


def _configured_build_for(project_root: Path, doxygen_output: Path) -> Path:
    """Return a configured build tree whose generators belong to ``project_root``.

    For the current checkout, the surrounding BESA CMake build is already configured and is the
    authoritative source of generated public headers.  sphinx-multiversion renders historical Git
    checkouts independently, so those refs receive a small private configure tree.  The docs layer
    does not invoke or know individual generators; configuring the project is what causes every
    registered generator to populate ``generated/<generator>/include``.
    """

    configured_source = os.environ.get("BESA_PROJECT_SOURCE_DIRECTORY")
    configured_binary = os.environ.get("BESA_PROJECT_BINARY_DIRECTORY")
    if configured_source and configured_binary:
        if Path(configured_source).resolve() == project_root.resolve():
            return Path(configured_binary).resolve()

    generated_build = doxygen_output / "project-build"
    shutil.rmtree(generated_build, ignore_errors=True)
    cmake = os.environ.get("BESA_CMAKE_EXECUTABLE", "cmake")
    subprocess.run(
        [
            cmake,
            "-S",
            str(project_root),
            "-B",
            str(generated_build),
            "-DPROJECT_FEATURES=~user-docs",
            "-DBUILD_TESTING=OFF",
            "-DRELEASE_TYPE=release",
        ],
        cwd=project_root,
        check=True,
    )
    if (project_root / "cmake" / "besa" / "generated.cmake").is_file():
        subprocess.run(
            [cmake, "--build", str(generated_build), "--target", "besa.generated"],
            cwd=project_root,
            check=True,
        )
    return generated_build


def _generated_include_directories(build_directory: Path) -> list[Path]:
    """Return all generator-owned public include roots in one configured build tree."""

    generated = build_directory / "generated"
    if not generated.is_dir():
        return []
    directories = [
        path.resolve()
        for path in generated.glob("*/include")
        if path.is_dir()
    ]
    # Compatibility for historical refs created before generator names became part of the path.
    legacy = generated / "include"
    if legacy.is_dir():
        directories.append(legacy.resolve())
    return sorted(set(directories))


def _configured_doxyfile(api_docs_directory: Path, configured_build: Path) -> Path:
    """Return the CMake-configured Doxyfile for this checkout.

    New checkouts configure ``api-docs/Doxyfile.in`` into their own CMake build tree so
    ``CLANG_DATABASE_PATH`` always points at that checkout's compilation database. Historical refs
    predating this mechanism may still contain a checked-in ``api-docs/Doxyfile``; keep that as a
    compatibility fallback so old API versions remain buildable.
    """

    configured = configured_build / "api-docs" / "Doxyfile"
    if configured.is_file():
        return configured

    legacy = api_docs_directory / "Doxyfile"
    if legacy.is_file():
        return legacy

    raise RuntimeError(
        "No configured Doxyfile was produced by CMake and no legacy api-docs/Doxyfile exists"
    )


def _prepare_public_include_tree(
    project_root: Path, doxygen_output: Path, configured_build: Path
) -> Path:
    """Stage the public header namespace Doxygen should expose.

    The staging tree mirrors the installed include namespace and adds developer-facing test support.
    Checked-in public headers come from ``src/*/include``, test support headers come from
    ``test/base/*/include``, and generated public headers come from every registered generator's
    ``<binary>/generated/<generator>/include`` root. Doxygen therefore has no knowledge of ``meta``
    or any future generator name.
    """

    public_include = doxygen_output / "public-include"
    shutil.rmtree(public_include, ignore_errors=True)
    public_include.mkdir(parents=True)

    for source_include in sorted(project_root.glob("src/*/include")):
        if source_include.is_dir():
            shutil.copytree(source_include, public_include, dirs_exist_ok=True)

    for test_include in sorted(project_root.glob("test/base/*/include")):
        if test_include.is_dir():
            shutil.copytree(test_include, public_include, dirs_exist_ok=True)

    for generated_include in _generated_include_directories(configured_build):
        shutil.copytree(generated_include, public_include, dirs_exist_ok=True)

    return public_include


def _prepare_api(app) -> None:
    """Prepare Doxygen/Breathe for the exact checkout Sphinx is about to render.

    This callback deliberately runs before Exhale's ``builder-inited`` callback. Exhale then sees
    the XML path for this checkout and generates its RST hierarchy from that XML only.
    """

    api_docs_directory = Path(app.srcdir).resolve()
    project_root = _api_project_root(api_docs_directory)
    checkout_version = _cmake_project_version(project_root)
    doxygen_output = _doxygen_output_for(project_root)

    # Exhale generates files into the active Sphinx source directory. For current-checkout builds
    # this is an external staged copy; for multiversion builds it is sphinx-multiversion's checkout.
    # Remove stale output first so deleted/renamed API entities cannot survive an incremental build.
    shutil.rmtree(api_docs_directory / "generated", ignore_errors=True)

    doxygen_output.mkdir(parents=True, exist_ok=True)
    configured_build = _configured_build_for(project_root, doxygen_output)
    public_include = _prepare_public_include_tree(project_root, doxygen_output, configured_build)
    base_config = _configured_doxyfile(api_docs_directory, configured_build).read_text(
        encoding="utf-8"
    )

    # Exhale places detailed entity pages one level below the API-version root in generated/. The
    # alias therefore needs one additional parent traversal compared with index.rst. Documentation
    # comments use semantic commands such as @projectdocs{reference/testing,the testing reference}
    # and never encode this physical site layout themselves.
    projectdocs_root = "../" * (_besa_properdocs_root_depth + 1)
    projectdocs_aliases = (
        f'ALIASES += "projectdocs=<a href=\\"{projectdocs_root}\\">main project documentation</a>"\n'
        f'ALIASES += "projectdocs{{1}}=<a href=\\"{projectdocs_root}\\1/\\">\\1</a>"\n'
        f'ALIASES += "projectdocs{{2}}=<a href=\\"{projectdocs_root}\\1/\\">\\2</a>"\n'
    )

    clang_options = _clang_options(configured_build)
    clang_options.append(f"-I{str(public_include).replace(chr(92), '/')}")

    generated_config = doxygen_output / "Doxyfile"
    generated_config.write_text(
        base_config
        + "\n"
        + f"CLANG_OPTIONS += {_doxygen_list(clang_options)}\n"
        + f'PROJECT_NUMBER = "{checkout_version}"\n'
        + f"OUTPUT_DIRECTORY = {_doxygen_quote(doxygen_output)}\n"
        + f"INPUT = {_doxygen_quote(public_include)}\n"
        + f"STRIP_FROM_PATH = {_doxygen_quote(public_include)}\n"
        + f"STRIP_FROM_INC_PATH = {_doxygen_quote(public_include)}\n"
        + projectdocs_aliases,
        encoding="utf-8",
    )

    # The current working-tree build has a stable Doxygen work directory across live reloads.
    # Remove the previous XML inventory explicitly so an entity deleted or reshaped by an
    # uncommitted edit cannot survive into the next Breathe/Exhale pass. Historical SMV checkouts
    # normally get checkout-specific work directories, but doing this unconditionally is harmless
    # and keeps both paths deterministic.
    shutil.rmtree(doxygen_output / "xml", ignore_errors=True)

    executable = os.environ.get("BESA_DOXYGEN_EXECUTABLE", "doxygen")
    subprocess.run(
        [executable, str(generated_config)],
        cwd=project_root,
        check=True,
    )

    # These values are consumed after builder-inited, so update Sphinx's live configuration rather
    # than module globals. In a sphinx-multiversion build this is what prevents old refs from reading
    # the current checkout's CMakeLists.txt or Doxygen XML.
    app.config.version = checkout_version
    app.config.release = checkout_version
    app.config.breathe_projects = {project: str(doxygen_output / "xml")}
    app.config.breathe_default_project = project

    # Exhale resolves path-valued entries in exhale_args relative to app.confdir. sphinx-multiversion
    # deliberately keeps app.confdir in the current checkout while app.srcdir points at the checkout
    # being rendered. Rewrite those entries to absolute paths under app.srcdir before Exhale's own
    # builder-inited callback runs, otherwise every historical ref tries to generate RST into the
    # current checkout and Exhale rejects containmentFolder as being outside that ref's source tree.
    checkout_exhale_args = dict(app.config.exhale_args)
    checkout_exhale_args["containmentFolder"] = str(api_docs_directory / "generated")
    checkout_exhale_args["doxygenStripFromPath"] = str(public_include)
    app.config.exhale_args = checkout_exhale_args


_API_SIMPLE_SYMBOL = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*")


def _cpp_domain_symbol_targets(app) -> dict[str, str]:
    """Map unambiguous qualified C/C++ names to the HTML targets Sphinx generated."""

    candidates: dict[str, set[str]] = {}
    for name, _display_name, _kind, docname, anchor, _priority in (
        app.env.get_domain("cpp").get_objects()
    ):
        # Sphinx includes function signatures in object names. The convenient @apidocs:: form is
        # intentionally available only when the unqualified signature is unambiguous.
        symbol = name.split("(", 1)[0].strip()
        if _API_SIMPLE_SYMBOL.fullmatch(symbol) is None:
            continue

        target = app.builder.get_target_uri(docname)
        if anchor:
            target = f"{target}#{anchor}"
        candidates.setdefault(symbol, set()).add(target)

    return {
        symbol: next(iter(targets))
        for symbol, targets in sorted(candidates.items())
        if len(targets) == 1
    }


def _write_api_symbol_aliases(app, exception) -> None:
    """Publish stable semantic URLs for ProperDocs ``@apidocs::...`` references."""

    if exception is not None:
        return

    output = Path(app.outdir).resolve()
    symbols = _cpp_domain_symbol_targets(app)
    for symbol, target in symbols.items():
        alias_directory = PurePosixPath("_symbols", *symbol.split("::"))
        alias = output.joinpath(*alias_directory.parts, "index.html")
        alias.parent.mkdir(parents=True, exist_ok=True)

        target_path, separator, fragment = target.partition("#")
        relative_target = posixpath.relpath(target_path, alias_directory.as_posix())
        if separator:
            relative_target = f"{relative_target}#{fragment}"

        escaped_target = html.escape(relative_target, quote=True)
        escaped_symbol = html.escape(symbol)
        alias.write_text(
            "\n".join(
                [
                    "<!doctype html>",
                    '<meta charset="utf-8">',
                    f'<meta http-equiv="refresh" content="0; url={escaped_target}">',
                    f'<link rel="canonical" href="{escaped_target}">',
                    f"<title>{escaped_symbol}</title>",
                    f'<p>Redirecting to <a href="{escaped_target}">{escaped_symbol}</a>.</p>',
                    "",
                ]
            ),
            encoding="utf-8",
        )

    (output / "symbols.json").write_text(
        json.dumps(
            {"project": project, "version": app.config.release, "symbols": symbols},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _xml_text(element: ET.Element | None) -> str:
    """Return all textual content below one Doxygen XML element."""

    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def _rst_role_title(value: str) -> str:
    """Escape syntax that has special meaning inside an RST role's display title.

    Sphinx interprets an unescaped ``<`` in role text as the start of the explicit target in
    ``title <target>`` syntax. C++ template arguments and operators therefore need escaping in the
    display half while the target half remains ordinary C++ syntax.
    """

    return re.sub(r"(?<!\\)<", r"\\<", value)


def _class_like_compounds(index_xml: Path) -> dict[str, tuple[str, str]]:
    """Return fully-qualified class/struct names and their Exhale identity."""

    root = ET.parse(index_xml).getroot()
    return {
        name: (compound.get("kind", ""), compound.get("refid", ""))
        for compound in root.findall("compound")
        if compound.get("kind") in {"class", "struct"}
        if (name := compound.findtext("name"))
        if compound.get("refid")
    }


def _class_like_names(index_xml: Path) -> set[str]:
    """Return fully-qualified class/struct names from one Doxygen index."""

    return set(_class_like_compounds(index_xml))


def _deduction_guide_names(index_xml: Path) -> set[str]:
    """Return namespace functions that are actually C++ class template deduction guides."""

    class_like = _class_like_names(index_xml)
    guides: set[str] = set()
    root = ET.parse(index_xml).getroot()
    for compound in root.findall("compound"):
        if compound.get("kind") != "namespace":
            continue
        namespace = compound.findtext("name") or ""
        if not namespace:
            continue
        for member in compound.findall("member"):
            if member.get("kind") != "function":
                continue
            name = member.findtext("name") or ""
            qualified = f"{namespace}::{name}" if name else ""
            if qualified in class_like:
                guides.add(qualified)
    return guides


def _namespace_function_counts(index_xml: Path) -> dict[str, int]:
    """Count free functions by qualified name, excluding class template deduction guides."""

    guides = _deduction_guide_names(index_xml)
    counts: dict[str, int] = {}
    root = ET.parse(index_xml).getroot()
    for compound in root.findall("compound"):
        if compound.get("kind") != "namespace":
            continue
        namespace = compound.findtext("name") or ""
        if not namespace:
            continue
        for member in compound.findall("member"):
            if member.get("kind") != "function":
                continue
            name = member.findtext("name") or ""
            qualified = f"{namespace}::{name}" if name else ""
            if not qualified or qualified in guides:
                continue
            counts[qualified] = counts.get(qualified, 0) + 1
    return counts


def _directive_function_name(target: str, names: set[str]) -> str | None:
    """Return the qualified name owning one ``doxygenfunction`` directive target."""

    for name in sorted(names, key=len, reverse=True):
        if target == name or target.startswith(f"{name}("):
            return name
    return None


def _mark_template_specializations_no_link(_index_xml: Path, generated: Path) -> None:
    """Render template specializations without registering duplicate C++ domain targets.

    Exhale gives primary templates and specializations separate pages.  Breathe/Sphinx can still
    normalize a constrained or partial specialization to the same C++ declaration as the primary
    template, which triggers ``duplicate_declaration.cpp`` under warnings-as-errors.

    Detect this from the generated Breathe directives themselves rather than from Doxygen's
    ``index.xml``.  Doxygen does not reliably preserve ``<...>`` in the index compound name for
    specializations, while Exhale's page directive does.  Only mark a ``<...>`` directive when a
    primary directive with the same base name is also present, so ordinary primary class templates
    remain canonical cross-reference targets.
    """

    directive = re.compile(
        r"^(?P<indent>\s*)\.\. doxygen(?:class|struct)::\s*(?P<target>.+?)\s*$"
    )
    pages: list[tuple[Path, list[str], int, re.Match[str]]] = []
    primary_names: set[str] = set()

    for page in generated.glob("*.rst"):
        lines = page.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            match = directive.match(line)
            if match is None:
                continue

            target = match.group("target").strip()
            base = target.split("<", 1)[0].strip()
            pages.append((page, lines, index, match))
            if "<" not in target:
                primary_names.add(base)
            break

    for page, lines, index, match in pages:
        target = match.group("target").strip()
        if "<" not in target:
            continue

        base = target.split("<", 1)[0].strip()
        if base not in primary_names:
            continue

        option_indent = f"{match.group('indent')}   "
        option_end = index + 1
        has_no_link = False
        while option_end < len(lines) and lines[option_end].startswith(option_indent + ":"):
            if lines[option_end].strip() == ":no-link:":
                has_no_link = True
                break
            option_end += 1
        if has_no_link:
            continue

        lines.insert(index + 1, f"{option_indent}:no-link:")
        page.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _neutralize_deduction_guide_pages(index_xml: Path, generated: Path) -> None:
    """Keep Exhale CTAD pages addressable without registering a duplicate C++ declaration.

    Exhale's file pages link to the standalone function page it creates for each deduction guide.
    Deleting that page removes the duplicate declaration but leaves those generated ``:ref:``
    targets dangling. Keep the page and its Exhale label, but replace only the Breathe function
    directive. The owning class page already renders the deduction guide.
    """

    guides = _deduction_guide_names(index_xml)
    if not guides:
        return
    directive = re.compile(r"^(?P<prefix>\s*\.\. doxygenfunction::\s*)(?P<target>.+?)\s*$")
    for path in generated.glob("*.rst"):
        lines = path.read_text(encoding="utf-8").splitlines()
        changed = False
        for index, line in enumerate(lines):
            match = directive.match(line)
            if match is None:
                continue
            if _directive_function_name(match.group("target"), guides) is None:
                continue
            lines[index] = (
                "Class template deduction guide; the declaration is documented with the owning "
                "class."
            )
            changed = True
        if changed:
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def _simplify_unique_function_directives(index_xml: Path, generated: Path) -> None:
    """Use name-only Breathe directives for non-overloaded free functions.

    Breathe can resolve a unique function from its qualified name alone. Avoiding Exhale's parsed
    parameter spelling makes variadic templates and other modern C++ signatures substantially less
    fragile while preserving explicit signatures for real overload sets.
    """

    counts = _namespace_function_counts(index_xml)
    unique = {name for name, count in counts.items() if count == 1}
    if not unique:
        return
    directive = re.compile(r"^(?P<prefix>\s*\.\. doxygenfunction::\s*)(?P<target>.+?)\s*$")
    for path in generated.glob("*.rst"):
        lines = path.read_text(encoding="utf-8").splitlines()
        changed = False
        for index, line in enumerate(lines):
            match = directive.match(line)
            if match is None:
                continue
            name = _directive_function_name(match.group("target"), unique)
            if name is None or match.group("target") == name:
                continue
            lines[index] = f"{match.group('prefix')}{name}"
            changed = True
        if changed:
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _concept_document_name(refid: str) -> str:
    """Return BESA's generated document name for one Doxygen concept."""

    slug = re.sub(r"[^A-Za-z0-9_]+", "_", refid).strip("_")
    return f"besa_concept_{slug}"


def _write_concept_pages(index_xml: Path, generated: Path) -> list[str]:
    """Generate the concept pages Exhale 0.3.x does not yet create itself."""

    documents: list[str] = []
    root = ET.parse(index_xml).getroot()
    for compound in root.findall("compound"):
        if compound.get("kind") != "concept":
            continue
        qualified = compound.findtext("name") or ""
        refid = compound.get("refid", "")
        if not qualified or not refid:
            continue
        title = qualified.rsplit("::", 1)[-1]
        document_name = _concept_document_name(refid)
        label = re.sub(r"[^A-Za-z0-9_]+", "_", f"besa_concept_{refid}")
        (generated / f"{document_name}.rst").write_text(
            "\n".join(
                [
                    f".. _{label}:",
                    "",
                    title,
                    "=" * len(title),
                    "",
                    f".. doxygenconcept:: {qualified}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        documents.append(f"{document_name}.rst")
    return documents


def _namespace_function_signatures(
    index_xml: Path,
) -> dict[tuple[str, str], list[tuple[str, str]]]:
    """Collect display signatures and Exhale labels for namespace functions."""

    result: dict[tuple[str, str], list[tuple[str, str]]] = {}
    class_like = _class_like_names(index_xml)
    root = ET.parse(index_xml).getroot()
    for compound in root.findall("compound"):
        if compound.get("kind") != "namespace":
            continue
        namespace = compound.findtext("name") or ""
        refid = compound.get("refid", "")
        compound_xml = index_xml.parent / f"{refid}.xml"
        if not namespace or not refid or not compound_xml.is_file():
            continue

        compound_root = ET.parse(compound_xml).getroot()
        for member in compound_root.findall(".//memberdef[@kind='function']"):
            name = member.findtext("name") or ""
            member_refid = member.get("id", "")
            if not name or not member_refid:
                continue
            qualified_name = member.findtext("qualifiedname") or f"{namespace}::{name}"
            if qualified_name in class_like:
                continue
            parameters: list[str] = []
            for parameter in member.findall("param"):
                parameter_type = _xml_text(parameter.find("type"))
                array = _xml_text(parameter.find("array"))
                if parameter_type:
                    parameters.append(f"{parameter_type}{array}")
            parameter_list = ", ".join(parameters)
            display = f"{name}({parameter_list})"
            result.setdefault((namespace, name), []).append(
                (display, f"exhale_function_{member_refid}")
            )

    for signatures in result.values():
        signatures[:] = sorted(set(signatures))
    return result


def _overload_document_name(namespace: str, function: str) -> str:
    """Return a stable Sphinx document name for one overload set."""

    slug = re.sub(r"[^A-Za-z0-9]+", "_", f"{namespace}_{function}").strip("_").lower()
    return f"api_overload_{slug}"


def _write_overload_pages(
    index_xml: Path, generated: Path
) -> dict[tuple[str, str], str]:
    """Write one compact document for each genuinely overloaded namespace function.

    Navigation links target Exhale's page labels instead of asking Sphinx's C++ parser to parse a
    complete dependent/template signature. Breathe still owns the detailed C++ declaration on the
    target page; the navigation layer only needs a stable document reference.
    """

    for stale in generated.glob("api_overload_*.rst"):
        stale.unlink()

    result: dict[tuple[str, str], str] = {}
    for (namespace, function), signatures in _namespace_function_signatures(index_xml).items():
        if len(signatures) < 2:
            continue

        document_name = _overload_document_name(namespace, function)
        title = function
        lines = [title, "=" * len(title), "", "Overloads", "---------", ""]
        for display, label in signatures:
            lines.append(f"* :ref:`{_rst_role_title(display)} <{label}>`")
        lines.append("")
        (generated / f"{document_name}.rst").write_text("\n".join(lines), encoding="utf-8")
        result[(namespace, function)] = document_name
    return result


def _replace_rst_heading(lines: list[str], index: int, title: str) -> None:
    """Replace one RST heading while preserving its adornment character."""

    if index + 1 >= len(lines) or not lines[index + 1]:
        return
    adornment = lines[index + 1][0]
    if any(character != adornment for character in lines[index + 1]):
        return
    lines[index] = title
    lines[index + 1] = adornment * len(title)


def _simplified_entity_title(title: str) -> str | None:
    """Return the compact display title for one Exhale entity title."""

    for prefix, kind in (
        ("Class ", "class"),
        ("Struct ", "struct"),
        ("Enum ", "enum"),
        ("Function ", "function"),
        ("Define ", "define"),
    ):
        if not title.startswith(prefix):
            continue
        value = title[len(prefix) :]
        if kind == "function" and "(" in value:
            name, parameters = value.split("(", 1)
            return f"{name.rsplit('::', 1)[-1]}({parameters}"
        return value.rsplit("::", 1)[-1]
    return None


def _simplify_generated_entity_pages(generated: Path) -> None:
    """Remove redundant kind prefixes and empty structural headings from Exhale entity pages.

    Detailed entity pages already identify the entity in their title and the declaration itself.
    A second ``Function Documentation`` / ``Struct Documentation`` heading adds no information and
    consumes substantial vertical space, so entity pages go directly from their provenance to the
    Breathe declaration.  Namespace pages retain their useful Classes / Enums / Functions sections.
    """

    documentation_headings = {
        "Class Documentation",
        "Struct Documentation",
        "Enum Documentation",
        "Function Documentation",
        "Define Documentation",
        "Documentation",
    }
    explicit_reference = re.compile(
        r":ref:`(?P<title>(?:Class|Struct|Enum|Function|Define) .+?) <(?P<target>exhale_[^`]+)>`"
    )

    for path in generated.glob("*.rst"):
        lines = path.read_text(encoding="utf-8").splitlines()
        changed = False
        is_entity_page = any(_simplified_entity_title(line) is not None for line in lines[:12])

        index = 0
        while index < len(lines):
            line = lines[index]
            if is_entity_page and line in documentation_headings:
                # Remove this before compacting entity-kind prefixes: ``Struct Documentation``
                # would otherwise be mistaken for an entity titled simply ``Documentation``.
                remove_count = 1
                if index + 1 < len(lines) and lines[index + 1]:
                    adornment = lines[index + 1][0]
                    if all(character == adornment for character in lines[index + 1]):
                        remove_count = 2
                del lines[index : index + remove_count]
                while index < len(lines) and lines[index] == "" and index > 0 and lines[index - 1] == "":
                    del lines[index]
                changed = True
                continue

            compact_title = _simplified_entity_title(line)
            if compact_title is not None:
                _replace_rst_heading(lines, index, compact_title)
                changed = True
                index += 2
                continue

            index += 1

        for index, line in enumerate(lines):
            def replace_reference(match: re.Match[str]) -> str:
                nonlocal changed
                compact = _simplified_entity_title(match.group("title"))
                if compact is None:
                    return match.group(0)
                changed = True
                return f":ref:`{_rst_role_title(compact)} <{match.group('target')}>`"

            lines[index] = explicit_reference.sub(replace_reference, line)

        if changed:
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _api_namespace_tree(
    index_xml: Path,
    generated: Path,
    *,
    root_namespace: str | None = None,
    include_root: bool = True,
    overload_pages: dict[tuple[str, str], str] | None = None,
) -> str:
    """Render the API below one namespace (or all root namespaces) as a recursive tree.

    Exhale namespace pages enumerate only immediate members.  BESA uses the same namespace model as
    the landing page to make every namespace page transitive: selecting ``foo`` exposes members of
    ``foo`` and of every descendant namespace while preserving the containment hierarchy.
    """

    root = ET.parse(index_xml).getroot()
    compounds = list(root.findall("compound"))
    namespace_names = {
        name
        for compound in compounds
        if compound.get("kind") == "namespace"
        if (name := compound.findtext("name"))
    }
    class_like = _class_like_compounds(index_xml)
    if overload_pages is None:
        overload_pages = _write_overload_pages(index_xml, generated)

    children: dict[str, set[str]] = {name: set() for name in namespace_names}
    members: dict[str, set[tuple[str, str, str, str]]] = {
        name: set() for name in namespace_names
    }
    function_counts: dict[tuple[str, str], int] = {}
    roots: set[str] = set()

    for namespace in namespace_names:
        parent = namespace.rsplit("::", 1)[0] if "::" in namespace else ""
        if parent in namespace_names:
            children[parent].add(namespace)
        else:
            roots.add(namespace)

    for compound in compounds:
        kind = compound.get("kind", "")
        name = compound.findtext("name") or ""
        if kind in {"class", "struct", "concept"} and "::" in name:
            parent, short_name = name.rsplit("::", 1)
            if parent in namespace_names:
                members[parent].add((kind, short_name, name, compound.get("refid", "")))
        if kind != "namespace" or name not in namespace_names:
            continue
        for member in compound.findall("member"):
            member_kind = member.get("kind", "")
            if member_kind not in {"enum", "function", "concept"}:
                continue
            member_name = member.findtext("name") or ""
            qualified_name = f"{name}::{member_name}" if member_name else ""
            if not qualified_name:
                continue
            if member_kind == "function" and qualified_name in class_like:
                # Doxygen exposes class template deduction guides as namespace functions as well as
                # part of the owning class. Keep only the class-owned representation.
                continue
            if member_kind == "function":
                key = (name, member_name)
                function_counts[key] = function_counts.get(key, 0) + 1
                if any(
                    existing_kind == "function" and existing_qualified == qualified_name
                    for existing_kind, _short, existing_qualified, _refid in members[name]
                ):
                    continue
            members[name].add(
                (member_kind, member_name, qualified_name, member.get("refid", ""))
            )

    markers = {
        "class": "C",
        "struct": "S",
        "enum": "E",
        "concept": "K",
        "function": "F",
    }
    lines = [
        ".. role:: api-kind",
        "",
        ":api-kind:`N` namespace  ·  :api-kind:`C` class  ·  :api-kind:`S` struct  ·  "
        ":api-kind:`E` enum  ·  :api-kind:`K` concept  ·  :api-kind:`F` function",
        "",
    ]

    def namespace_link(namespace: str) -> str:
        short_name = namespace.rsplit("::", 1)[-1]
        # Exhale gives namespace pages stable labels derived from the qualified name. ``::`` becomes
        # ``__``; use the label rather than depending on Exhale's generated filename.
        target = "namespace_" + namespace.replace(":", "_").replace(os.sep, "_").replace(" ", "_")
        return f":ref:`{short_name} <{target}>`"

    def emit_item(text: str, depth: int) -> None:
        # reStructuredText requires a blank line before a nested bullet list. Emitting every tree
        # item as a small paragraph keeps arbitrary namespace depths valid and readable.
        lines.append(f"{'  ' * depth}* {text}")
        lines.append("")

    def emit_member(
        namespace: str, member: tuple[str, str, str, str], depth: int
    ) -> None:
        kind, short_name, _qualified_name, refid = member
        marker = markers[kind]
        display_name = f"{short_name}()" if kind == "function" else short_name
        escaped_display = _rst_role_title(display_name)
        if kind == "function" and function_counts.get((namespace, short_name), 0) > 1:
            target = overload_pages.get((namespace, short_name))
            if target:
                link = f":doc:`{escaped_display} </generated/{target}>`"
            else:
                link = f"``{display_name}``"
        elif refid:
            if kind == "concept":
                label = re.sub(r"[^A-Za-z0-9_]+", "_", f"besa_concept_{refid}")
            else:
                label = f"exhale_{kind}_{refid}"
            link = f":ref:`{escaped_display} <{label}>`"
        else:
            link = f"``{display_name}``"
        emit_item(f":api-kind:`{marker}` {link}", depth)

    def emit_namespace(namespace: str, depth: int) -> None:
        emit_item(f":api-kind:`N` {namespace_link(namespace)}", depth)
        for child in sorted(children[namespace]):
            emit_namespace(child, depth + 1)
        for member in sorted(members[namespace], key=lambda item: (item[1].lower(), item[0])):
            emit_member(namespace, member, depth + 1)

    if root_namespace is None:
        for namespace in sorted(roots):
            emit_namespace(namespace, 0)
        if not roots:
            lines.append("No public namespaces were discovered.")
    elif root_namespace not in namespace_names:
        lines.append("No public members were discovered.")
    elif include_root:
        emit_namespace(root_namespace, 0)
    else:
        # The namespace page title already names the root. Show its own members and recursively
        # expand every child namespace below it, without adding a redundant root item to the tree.
        for child in sorted(children[root_namespace]):
            emit_namespace(child, 0)
        for member in sorted(
            members[root_namespace], key=lambda item: (item[1].lower(), item[0])
        ):
            emit_member(root_namespace, member, 0)
        if not children[root_namespace] and not members[root_namespace]:
            lines.append("No public members were discovered.")

    return "\n".join(lines) + "\n"


def _api_namespace_overview(
    index_xml: Path,
    generated: Path,
    overload_pages: dict[tuple[str, str], str] | None = None,
) -> str:
    """Build the recursive namespace-oriented API synopsis for the landing page."""

    return _api_namespace_tree(
        index_xml,
        generated,
        overload_pages=overload_pages,
    )


_NAMESPACE_MEMBER_HEADINGS = {
    "Namespaces",
    "Classes",
    "Structs",
    "Unions",
    "Concepts",
    "Enums",
    "Functions",
    "Variables",
    "Typedefs",
    "Defines",
}


def _namespace_page_member_start(lines: list[str]) -> int | None:
    """Return the first Exhale immediate-member section on a namespace page."""

    for index, line in enumerate(lines[:-1]):
        if line not in _NAMESPACE_MEMBER_HEADINGS or not lines[index + 1]:
            continue
        adornment = lines[index + 1][0]
        if adornment == "-" and all(character == adornment for character in lines[index + 1]):
            return index
    return None


def _rewrite_namespace_pages(
    index_xml: Path,
    generated: Path,
    overload_pages: dict[tuple[str, str], str],
) -> None:
    """Replace Exhale's immediate-only namespace listings with recursive member trees.

    Everything before Exhale's first member-kind section is retained, including the namespace title,
    contents directive, and any namespace prose. Only the member enumeration is replaced.
    """

    root = ET.parse(index_xml).getroot()
    for compound in root.findall("compound"):
        if compound.get("kind") != "namespace":
            continue
        namespace = compound.findtext("name") or ""
        refid = compound.get("refid", "")
        if not namespace or not refid:
            continue

        page = generated / f"{refid}.rst"
        if not page.is_file():
            # Doxygen refids normally are Exhale filenames. Fall back to Exhale's stable namespace
            # label for compatibility with historical generator naming.
            label = "namespace_" + namespace.replace(":", "_").replace(" ", "_")
            for candidate in generated.glob("*.rst"):
                head = "\n".join(candidate.read_text(encoding="utf-8").splitlines()[:16])
                if f".. _{label}:" in head:
                    page = candidate
                    break
        if not page.is_file():
            continue

        lines = page.read_text(encoding="utf-8").splitlines()
        start = _namespace_page_member_start(lines)
        if start is None:
            while lines and lines[-1] == "":
                lines.pop()
            prefix = lines
        else:
            prefix = lines[:start]
            while prefix and prefix[-1] == "":
                prefix.pop()

        tree = _api_namespace_tree(
            index_xml,
            generated,
            root_namespace=namespace,
            include_root=False,
            overload_pages=overload_pages,
        ).rstrip()
        replacement = [*prefix, "", "Members", "-------", "", tree, ""]
        page.write_text("\n".join(replacement), encoding="utf-8")


def _unabridged_documents(unabridged: Path) -> list[str]:
    """Extract Exhale's generated document list for one invisible root toctree."""

    if not unabridged.is_file():
        return []
    documents: list[str] = []
    for line in unabridged.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s{3}(.+\.rst)\s*$", line)
        if match and match.group(1) not in documents:
            documents.append(match.group(1))
    return documents


def _prepare_api_landing(app) -> None:
    """Build the compact namespace/file synopsis used by the API landing page.

    New BESA projects include ``generated/api_landing.rst.include`` directly from ``index.rst`` so
    the API reference opens on the useful namespace/file hierarchy instead of an intermediate
    ``<project> API`` page. Historical Git refs may still contain the old index that points at
    Exhale's ``library_root.rst``; preserve that layout when rendering those refs so current BESA
    configuration remains compatible with already-published tags.
    """

    api_docs_directory = Path(app.srcdir).resolve()
    generated = api_docs_directory / "generated"
    root_file = generated / "library_root.rst"
    file_hierarchy = generated / "file_view_hierarchy.rst.include"
    unabridged = generated / "unabridged_api.rst.include"
    xml_directory = Path(app.config.breathe_projects[project])
    index_xml = xml_directory / "index.xml"
    index_source = api_docs_directory / "index.rst"

    if not index_xml.is_file() or not root_file.is_file() or not index_source.is_file():
        return

    _mark_template_specializations_no_link(index_xml, generated)
    _neutralize_deduction_guide_pages(index_xml, generated)
    _simplify_unique_function_directives(index_xml, generated)
    _simplify_generated_entity_pages(generated)
    concept_documents = _write_concept_pages(index_xml, generated)

    overload_pages = _write_overload_pages(index_xml, generated)
    overview = generated / "api_namespace_overview.rst.include"
    overview.write_text(
        _api_namespace_overview(index_xml, generated, overload_pages),
        encoding="utf-8",
    )
    _rewrite_namespace_pages(index_xml, generated, overload_pages)

    documents = [
        document
        for document in _unabridged_documents(unabridged)
        if (generated / document).is_file()
    ]
    documents.extend(document for document in concept_documents if document not in documents)
    documents.extend(
        path.name for path in sorted(generated.glob("api_overload_*.rst")) if path.name not in documents
    )

    merged_landing = "generated/api_landing.rst.include" in index_source.read_text(encoding="utf-8")
    lines = [
        "Namespace hierarchy",
        "-------------------",
        "",
        ".. include:: /generated/api_namespace_overview.rst.include",
        "",
    ]
    if file_hierarchy.is_file():
        lines.extend(
            [
                ".. include:: /generated/file_view_hierarchy.rst.include",
                "",
            ]
        )
    if documents:
        lines.extend(
            [
                ".. toctree::",
                "   :hidden:",
                "   :maxdepth: 1",
                "",
                *[f"   /generated/{Path(document).with_suffix('').as_posix()}" for document in documents],
                "",
            ]
        )

    if merged_landing:
        landing = generated / "api_landing.rst.include"
        landing.write_text("\n".join(lines), encoding="utf-8")
        # Exhale requires a root file while generating, but the merged index owns navigation in new
        # projects. Keep the generated root out of Sphinx's orphan checks and out of the public UI.
        root_file.write_text(":orphan:\n", encoding="utf-8")
        return

    # Compatibility path for historical refs created before BESA merged the two landing pages.
    title = f"{project} API"
    legacy_lines = [title, "=" * len(title), "", *lines]
    root_file.write_text("\n".join(legacy_lines), encoding="utf-8")


def _api_sidebar_namespaces(app) -> list[dict[str, str]]:
    """Return the public namespaces and their generated Sphinx documents.

    The global left sidebar intentionally contains namespaces only.  Exhale filenames are normally
    Doxygen refids, but historical versions have used different namespace filenames, so fall back
    to Exhale's stable namespace label when resolving the generated page.
    """

    cached = getattr(app, "_besa_api_sidebar_namespaces", None)
    if cached is not None:
        return cached

    generated = Path(app.srcdir).resolve() / "generated"
    xml_directory = Path(app.config.breathe_projects[project])
    index_xml = xml_directory / "index.xml"
    if not generated.is_dir() or not index_xml.is_file():
        app._besa_api_sidebar_namespaces = []
        return []

    label_documents: dict[str, str] = {}
    for candidate in generated.glob("namespace*.rst"):
        for line in candidate.read_text(encoding="utf-8").splitlines()[:16]:
            match = re.match(r"^\.\. _([^:]+):$", line)
            if match:
                label_documents[match.group(1)] = f"generated/{candidate.stem}"

    entries: list[dict[str, str]] = []
    root = ET.parse(index_xml).getroot()
    for compound in root.findall("compound"):
        if compound.get("kind") != "namespace":
            continue
        namespace = compound.findtext("name") or ""
        refid = compound.get("refid") or ""
        if not namespace:
            continue

        document = ""
        direct = generated / f"{refid}.rst"
        if refid and direct.is_file():
            document = f"generated/{direct.stem}"
        else:
            label = "namespace_" + namespace.replace(":", "_").replace(" ", "_")
            document = label_documents.get(label, "")

        if document:
            entries.append({"name": namespace, "document": document})

    entries.sort(key=lambda item: item["name"].casefold())
    app._besa_api_sidebar_namespaces = entries
    return entries


def _api_sidebar_context(app, pagename, _templatename, context, _doctree) -> None:
    """Expose the namespace-only API navigation to the custom PyData sidebar template."""

    context["besa_api_sidebar_namespaces"] = _api_sidebar_namespaces(app)
    context["besa_api_sidebar_current"] = pagename


def _mark_multiline_signatures(_app, doctree) -> None:
    """Mark signatures whose parameter list Sphinx chose to render on logical lines.

    The C++ domain owns the 122-character decision. This callback only exposes that decision as a
    CSS class so BESA can move a return type onto its own line without reimplementing Sphinx's
    signature-length calculation. Import Sphinx lazily so the generated conf.py remains importable
    by BESA's template tests even when Sphinx is not installed in that test environment.
    """

    from sphinx import addnodes

    for signature in doctree.findall(addnodes.desc_signature):
        parameter_lists = signature.findall(addnodes.desc_parameterlist)
        if any(node.get("multi_line_parameter_list", False) for node in parameter_lists):
            classes = signature.setdefault("classes", [])
            if "besa-multiline-signature" not in classes:
                classes.append("besa-multiline-signature")


def setup(app) -> None:
    """Generate checkout-specific XML before Exhale expands it into Sphinx pages."""

    # Sphinx invokes event listeners in ascending priority. Exhale uses builder-inited too, so run
    # before the normal extension priority (500).
    app.connect("builder-inited", _prepare_api, priority=100)
    # Exhale writes its generated RST during builder-inited at the normal extension priority.
    # Run afterwards, but still before Sphinx discovers source documents.  In particular, overload
    # pages must exist at discovery time or Sphinx will report them as unknown/nonexistent docs.
    app.connect("builder-inited", _prepare_api_landing, priority=900)
    app.connect("doctree-read", _mark_multiline_signatures)
    app.connect("html-page-context", _api_sidebar_context)
    app.connect("build-finished", _write_api_symbol_aliases)
