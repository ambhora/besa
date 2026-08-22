# --------------------------------------------------------------------------------------------------
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
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

CONFIG_DIRECTORY = Path(__file__).resolve().parent

project = "vorlage"
author = ""


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
version = release = _cmake_project_version(CONFIG_DIRECTORY.parent)

extensions = [
    "breathe",
    "exhale",
    "sphinx_multiversion",
]

templates_path = ["_templates"]
html_static_path = ["_static"]
html_css_files = ["css/besa-api.css"]
html_js_files = ["js/besa-api-version.js", "js/besa-api-presentation.js"]
exclude_patterns: list[str] = []

html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "navbar_align": "left",
    "navbar_end": ["project-links.html", "theme-switcher", "navbar-icon-links"],
    "secondary_sidebar_items": ["page-toc"],
    "show_prev_next": True,
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

# sphinx-multiversion defaults already select local branch heads and tags. Keep that explicit so the
# generated project's publication model is visible in one place.
smv_branch_whitelist = r"^.*$"
smv_tag_whitelist = r"^.*$"
smv_outputdir_format = r"{ref.name}"

# Exhale automatically emits the complete API model represented by Doxygen XML. No class/function
# selection list is maintained by the project. Generated RST lives below api-docs/generated and is
# ignored by Git; individual namespace/class/file pages remain separate for large APIs.
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


def _prepare_public_include_tree(project_root: Path, doxygen_output: Path) -> Path:
    """Stage the public header namespace Doxygen should expose.

    The staging tree mirrors the installed include namespace. Checked-in public headers come from
    ``src/*/include`` and generated public headers come from every registered generator's
    ``<binary>/generated/<generator>/include`` root. Doxygen therefore has no knowledge of ``meta``
    or any future generator name.
    """

    public_include = doxygen_output / "public-include"
    shutil.rmtree(public_include, ignore_errors=True)
    public_include.mkdir(parents=True)

    for source_include in sorted(project_root.glob("src/*/include")):
        if source_include.is_dir():
            shutil.copytree(source_include, public_include, dirs_exist_ok=True)

    configured_build = _configured_build_for(project_root, doxygen_output)
    for generated_include in _generated_include_directories(configured_build):
        shutil.copytree(generated_include, public_include, dirs_exist_ok=True)

    return public_include


def _prepare_api(app) -> None:
    """Prepare Doxygen/Breathe for the exact checkout Sphinx is about to render.

    This callback deliberately runs before Exhale's ``builder-inited`` callback. Exhale then sees
    the XML path for this checkout and generates its RST hierarchy from that XML only.
    """

    api_docs_directory = Path(app.srcdir).resolve()
    project_root = api_docs_directory.parent
    checkout_version = _cmake_project_version(project_root)
    doxygen_output = _doxygen_output_for(project_root)

    # Exhale generates files into the active checkout's Sphinx source directory. Remove stale output
    # first so deleted/renamed API entities cannot survive an incremental current-checkout build.
    shutil.rmtree(api_docs_directory / "generated", ignore_errors=True)

    doxygen_output.mkdir(parents=True, exist_ok=True)
    public_include = _prepare_public_include_tree(project_root, doxygen_output)
    base_config = (api_docs_directory / "Doxyfile").read_text(encoding="utf-8")
    generated_config = doxygen_output / "Doxyfile"
    generated_config.write_text(
        base_config
        + "\n"
        + f'PROJECT_NUMBER = "{checkout_version}"\n'
        + f"OUTPUT_DIRECTORY = {_doxygen_quote(doxygen_output)}\n"
        + f"INPUT = {_doxygen_quote(public_include)}\n"
        + f"STRIP_FROM_PATH = {_doxygen_quote(public_include)}\n"
        + f"STRIP_FROM_INC_PATH = {_doxygen_quote(public_include)}\n",
        encoding="utf-8",
    )

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



def _generated_namespace_pages(generated: Path) -> dict[str, str]:
    """Map fully-qualified namespaces to their Exhale document names."""

    result: dict[str, str] = {}
    pattern = re.compile(r"^\.\. doxygennamespace::\s+(.+?)\s*$", flags=re.MULTILINE)
    for path in generated.rglob("*.rst"):
        if path.name == "library_root.rst":
            continue
        match = pattern.search(path.read_text(encoding="utf-8"))
        if match:
            result[match.group(1)] = path.relative_to(generated).with_suffix("").as_posix()
    return result


def _xml_text(element: ET.Element | None) -> str:
    """Return all textual content below one Doxygen XML element."""

    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def _namespace_function_signatures(
    index_xml: Path,
) -> dict[tuple[str, str], list[tuple[str, str]]]:
    """Collect display signatures and exact C++ cross-reference targets for namespace functions."""

    result: dict[tuple[str, str], list[tuple[str, str]]] = {}
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
            if not name:
                continue
            qualified_name = member.findtext("qualifiedname") or f"{namespace}::{name}"
            return_type = _xml_text(member.find("type"))
            parameters: list[str] = []
            for parameter in member.findall("param"):
                parameter_type = _xml_text(parameter.find("type"))
                array = _xml_text(parameter.find("array"))
                if parameter_type:
                    parameters.append(f"{parameter_type}{array}")
            parameter_list = ", ".join(parameters)
            display = f"{name}({parameter_list})"
            declaration = f"{qualified_name}({parameter_list})"
            if return_type:
                declaration = f"{return_type} {declaration}"
            result.setdefault((namespace, name), []).append((display, declaration))

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
    """Write one compact document for each genuinely overloaded namespace function."""

    for stale in generated.glob("api_overload_*.rst"):
        stale.unlink()

    result: dict[tuple[str, str], str] = {}
    for (namespace, function), signatures in _namespace_function_signatures(index_xml).items():
        if len(signatures) < 2:
            continue

        document_name = _overload_document_name(namespace, function)
        title = function
        lines = [title, "=" * len(title), "", "Overloads", "---------", ""]
        for display, declaration in signatures:
            # Sphinx's C++ domain resolves a complete function declaration to one exact overload.
            # This keeps the overload-set page compact while every entry still reaches its own
            # detailed Breathe documentation.
            lines.append(f"* :cpp:func:`{display} <{declaration}>`")
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
        "Documentation",
    }
    explicit_reference = re.compile(
        r":ref:`(?P<title>(?:Class|Struct|Enum|Function) .+?) <(?P<target>[^<>]+)>`"
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
                return f":ref:`{compact} <{match.group('target')}>`"

            lines[index] = explicit_reference.sub(replace_reference, line)

        if changed:
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _api_namespace_overview(index_xml: Path, generated: Path) -> str:
    """Build a compact namespace-oriented API index from Doxygen's index XML.

    The landing page is deliberately a synopsis.  Classes, structs, enums, and functions are
    listed directly below the namespace that owns them, and overloaded functions are represented
    once by name.  Detailed signatures remain on the generated namespace/entity pages.
    """

    root = ET.parse(index_xml).getroot()
    compounds = list(root.findall("compound"))
    namespace_names = {
        name
        for compound in compounds
        if compound.get("kind") == "namespace"
        if (name := compound.findtext("name"))
    }
    namespace_pages = _generated_namespace_pages(generated)
    overload_pages = _write_overload_pages(index_xml, generated)

    children: dict[str, set[str]] = {name: set() for name in namespace_names}
    members: dict[str, set[tuple[str, str, str]]] = {name: set() for name in namespace_names}
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
        if kind in {"class", "struct"} and "::" in name:
            parent, short_name = name.rsplit("::", 1)
            if parent in namespace_names:
                members[parent].add((kind, short_name, name))
        if kind != "namespace" or name not in namespace_names:
            continue
        for member in compound.findall("member"):
            member_kind = member.get("kind", "")
            if member_kind not in {"enum", "function"}:
                continue
            member_name = member.findtext("name") or ""
            if member_name:
                members[name].add((member_kind, member_name, f"{name}::{member_name}"))
                if member_kind == "function":
                    key = (name, member_name)
                    function_counts[key] = function_counts.get(key, 0) + 1

    markers = {
        "class": "C",
        "struct": "S",
        "enum": "E",
        "function": "F",
    }
    roles = {
        "class": "cpp:class",
        "struct": "cpp:struct",
        "enum": "cpp:enum",
        "function": "cpp:func",
    }

    lines = [
        ".. role:: api-kind",
        "",
        ":api-kind:`N` namespace  ·  :api-kind:`C` class  ·  :api-kind:`S` struct  ·  "
        ":api-kind:`E` enum  ·  :api-kind:`F` function",
        "",
    ]

    def namespace_link(namespace: str) -> str:
        short_name = namespace.rsplit("::", 1)[-1]
        target = namespace_pages.get(namespace)
        if target:
            # Use an absolute Sphinx document path so namespace links remain valid when this
            # overview is included from Exhale's generated root and in sphinx-multiversion refs.
            return f":doc:`{short_name} </generated/{target}>`"
        return f"``{short_name}``"

    def emit_item(text: str, depth: int) -> None:
        # reStructuredText requires a blank line before a nested bullet list.  Emitting every
        # tree item as a small paragraph keeps arbitrary namespace depths valid and readable.
        lines.append(f"{'  ' * depth}* {text}")
        lines.append("")

    def emit_namespace(namespace: str, depth: int) -> None:
        emit_item(f":api-kind:`N` {namespace_link(namespace)}", depth)
        for child in sorted(children[namespace]):
            emit_namespace(child, depth + 1)
        for kind, short_name, qualified_name in sorted(
            members[namespace], key=lambda item: (item[1].lower(), item[0])
        ):
            marker = markers[kind]
            display_name = f"{short_name}()" if kind == "function" else short_name
            if kind == "function" and function_counts.get((namespace, short_name), 0) > 1:
                target = overload_pages.get((namespace, short_name))
                if target:
                    link = f":doc:`{display_name} </generated/{target}>`"
                else:
                    link = f"``{display_name}``"
            else:
                role = roles[kind]
                link = f":{role}:`{display_name} <{qualified_name}>`"
            emit_item(f":api-kind:`{marker}` {link}", depth + 1)

    for namespace in sorted(roots):
        emit_namespace(namespace, 0)

    if not roots:
        lines.append("No public namespaces were discovered.")

    return "\n".join(lines) + "\n"

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
    """Replace Exhale's noisy root page with a compact namespace synopsis."""

    api_docs_directory = Path(app.srcdir).resolve()
    generated = api_docs_directory / "generated"
    root_file = generated / "library_root.rst"
    file_hierarchy = generated / "file_view_hierarchy.rst.include"
    unabridged = generated / "unabridged_api.rst.include"
    xml_directory = Path(app.config.breathe_projects[project])
    index_xml = xml_directory / "index.xml"

    if not index_xml.is_file() or not root_file.is_file():
        return

    _simplify_generated_entity_pages(generated)

    overview = generated / "api_namespace_overview.rst.include"
    overview.write_text(_api_namespace_overview(index_xml, generated), encoding="utf-8")

    title = f"{project} API"
    lines = [
        title,
        "=" * len(title),
        "",
        "Namespace hierarchy",
        "-------------------",
        "",
        ".. include:: api_namespace_overview.rst.include",
        "",
    ]
    if file_hierarchy.is_file():
        lines.extend(
            [
                ".. include:: file_view_hierarchy.rst.include",
                "",
            ]
        )

    documents = _unabridged_documents(unabridged)
    documents.extend(
        path.name for path in sorted(generated.glob("api_overload_*.rst")) if path.name not in documents
    )
    if documents:
        lines.extend(
            [
                ".. toctree::",
                "   :hidden:",
                "   :maxdepth: 1",
                "",
                *[f"   {document}" for document in documents],
                "",
            ]
        )

    root_file.write_text("\n".join(lines), encoding="utf-8")

def setup(app) -> None:
    """Generate checkout-specific XML before Exhale expands it into Sphinx pages."""

    # Sphinx invokes event listeners in ascending priority. Exhale uses builder-inited too, so run
    # before the normal extension priority (500).
    app.connect("builder-inited", _prepare_api, priority=100)
    # Exhale writes its generated RST during builder-inited at the normal extension priority.
    # Run afterwards, but still before Sphinx discovers source documents.  In particular, overload
    # pages must exist at discovery time or Sphinx will report them as unknown/nonexistent docs.
    app.connect("builder-inited", _prepare_api_landing, priority=900)
