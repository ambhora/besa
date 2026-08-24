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

import copy
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
import tomllib
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


def _project_version(project_root: Path) -> str:
    """Read the project version from one concrete checkout.

    ``besa.toml`` is authoritative for schema-v1 projects.  The CMake parser is retained only for
    historical refs created before the declarative project model existed.
    """

    model = project_root / "besa.toml"
    if model.is_file():
        try:
            data = tomllib.loads(model.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            data = {}
        project_table = data.get("project", {}) if isinstance(data, dict) else {}
        if isinstance(project_table, dict):
            value = project_table.get("version")
            if isinstance(value, str) and value:
                return value

    cmake_path = project_root / "CMakeLists.txt"
    if cmake_path.is_file():
        cmake = cmake_path.read_text(encoding="utf-8")
        match = re.search(
            r"project\s*\([^)]*?\bVERSION\s+([0-9]+(?:\.[0-9]+){1,3})",
            cmake,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if match:
            return match.group(1)
    return "0.0.0"


# These import-time values make direct ``sphinx-build`` configuration introspection useful. They are
# replaced from ``app.srcdir`` before an actual builder starts, which is essential for multiversion.
version = release = _project_version(_api_project_root(CONFIG_DIRECTORY))

extensions = [
    "besa_exhale_compat",
    "breathe",
    "exhale",
    "sphinx.ext.graphviz",
    "sphinx_multiversion",
]

graphviz_output_format = "svg"

templates_path = ["_templates"]
html_static_path = ["_static"]
html_css_files = ["css/besa-api.css", "css/besa-api-desktop.css"]
html_js_files = [
    "js/besa-api-version.js",
    "js/besa-api-source-locations.js",
    "js/besa-api-presentation.js",
]
exclude_patterns: list[str] = []

# Vorlage's portability qualifiers are ordinary preprocessor macros, but Doxygen deliberately keeps
# their API-facing spelling in declarations so one merged CPU/CUDA/HIP reference can describe the
# abstraction rather than whichever compiler happened to build the docs.  Tell Sphinx's C++ parser
# that these identifier-like macros are attributes; otherwise Breathe hands it valid declarations
# such as ``BESA_PROJECT_UPPER_HOST_DEVICE constexpr auto begin()`` which the C++ domain cannot parse.
cpp_id_attributes = [
    "BESA_PROJECT_UPPER_HOST",
    "BESA_PROJECT_UPPER_DEVICE",
    "BESA_PROJECT_UPPER_GLOBAL",
    "BESA_PROJECT_UPPER_HOST_DEVICE",
]

# Long C++ signatures use Sphinx's native logical-line formatting. Sphinx decides whether a
# parameter list is multiline from the rendered signature length, so short declarations remain
# compact and individual directives can still opt out with :single-line-parameter-list:.
cpp_maximum_signature_line_length = 122

html_theme = "pydata_sphinx_theme"
# Keep the navbar title version-independent. The selected API version is shown by the dedicated
# version selector, while Sphinx multiversion builds can otherwise inherit the current checkout
# release in the title even when rendering a historical ref.
html_title = f"{project} API documentation"
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

# Keep the global API navigation namespace-oriented. The custom sidebar renders namespaces as a
# collapsible outline and shows each namespace's immediate public entities underneath it.
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



def _read_api_manifest(build_directory: Path) -> dict[str, object] | None:
    """Read the BESA API manifest produced by one configured build, if available."""

    path = build_directory / "besa" / "api-manifest.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Cannot read BESA API manifest {path}: {error}") from error
    if data.get("schema_version") != 1:
        raise RuntimeError(f"Unsupported BESA API manifest schema in {path}")
    return data


def _configure_api_discovery(
    project_root: Path, build_directory: Path, *, profile: str | None = None
) -> dict[str, object] | None:
    """Configure one compiler-free BESA API-discovery build and return its manifest when supported."""

    shutil.rmtree(build_directory, ignore_errors=True)
    cmake = os.environ.get("BESA_CMAKE_EXECUTABLE", "cmake")
    command = [
        cmake,
        "-S",
        str(project_root),
        "-B",
        str(build_directory),
        "-DBESA_API_DISCOVERY_ONLY=ON",
        "-DBUILD_TESTING=OFF",
        "-DPROJECT_DEVTOOLS=none",
        "-DPROJECT_WARNINGS=none",
        "-DRELEASE_TYPE=release",
    ]
    if profile:
        command.append(f"-DBESA_API_PROFILE={profile}")
    subprocess.run(command, cwd=project_root, check=True)
    return _read_api_manifest(build_directory)


def _api_profile_catalog(
    project_root: Path, doxygen_output: Path, configured_build: Path
) -> dict[str, object]:
    """Return profile declarations without requiring the current build to have been reconfigured."""

    manifest = _read_api_manifest(configured_build)
    if manifest is not None and manifest.get("profiles"):
        return manifest
    discovered = _configure_api_discovery(project_root, doxygen_output / "profile-catalog")
    return discovered or {"schema_version": 0, "profiles": [], "registrations": []}


def _profile_public_include_tree(
    project_root: Path,
    profile_build: Path,
    doxygen_output: Path,
    profile_name: str,
    manifest: dict[str, object],
) -> Path:
    """Stage only API-classified roots selected by one API profile."""

    public_include = doxygen_output / "profiles" / profile_name / "public-include"
    shutil.rmtree(public_include, ignore_errors=True)
    public_include.mkdir(parents=True)

    registrations = manifest.get("registrations", [])
    if not isinstance(registrations, list):
        raise RuntimeError(f"Invalid registrations in API profile {profile_name!r}")

    if not registrations:
        # Compatibility for historical refs predating API classifications/profiles.
        for source_include in sorted(project_root.glob("src/*/include")):
            if source_include.is_dir():
                shutil.copytree(source_include, public_include, dirs_exist_ok=True)
        for generated_include in _generated_include_directories(profile_build):
            shutil.copytree(generated_include, public_include, dirs_exist_ok=True)

    for registration in registrations:
        if not isinstance(registration, dict):
            continue
        if not registration.get("selected") or registration.get("api") == "none":
            continue
        kind = registration.get("kind")
        relative = registration.get("path")
        base = registration.get("base")
        if not isinstance(relative, str) or base not in {"source", "binary"}:
            continue
        root = (project_root if base == "source" else profile_build) / relative
        if kind in {"source-directory", "directory"}:
            root = root / "include"
        if root.is_dir():
            shutil.copytree(root, public_include, dirs_exist_ok=True)

    # The generated project exposes developer-facing test support as part of the reference today. Treat each
    # ``test/base/<toolchain>/include`` tree like the corresponding toolchain feature so profile
    # fixtures can exercise configuration-specific API discovery without leaking into every
    # profile. For example, ``test/base/cuda/include`` is visible only when ``toolchain-cuda`` is
    # enabled, while ``test/base/cpp/include`` is visible in CPU, CUDA, and HIP profiles because
    # all three profiles include ``toolchain-cpp``. Historical manifests without feature data keep
    # the old include-everything behavior.
    active_features_value = manifest.get("active_features", [])
    active_features = (
        {str(value) for value in active_features_value}
        if isinstance(active_features_value, list)
        else set()
    )
    for test_include in sorted(project_root.glob("test/base/*/include")):
        if not test_include.is_dir():
            continue
        toolchain = test_include.parent.name
        required_feature = f"toolchain-{toolchain}"
        if active_features and required_feature not in active_features:
            continue
        shutil.copytree(test_include, public_include, dirs_exist_ok=True)

    return public_include


def _profile_predefined(profile: dict[str, object]) -> list[str]:
    values = profile.get("predefined", [])
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if str(value)]


def _profile_clang_defines(predefined: list[str]) -> list[str]:
    options = [f"-D{value}" for value in predefined]
    names = {value.split("=", 1)[0] for value in predefined}
    if "__CUDACC__" in names or "__HIPCC__" in names:
        # These compiler keywords are meaningful to CUDA/HIP compilers but ordinary libclang needs
        # harmless stand-ins while it parses the same public header inventory.
        options.extend(["-D__host__=", "-D__device__=", "-D__global__="])
    return options


def _projectdocs_aliases() -> str:
    projectdocs_root = "../" * (_besa_properdocs_root_depth + 1)
    return (
        f'ALIASES += "projectdocs=<a href=\\"{projectdocs_root}\\">main project documentation</a>"\n'
        f'ALIASES += "projectdocs{{1}}=<a href=\\"{projectdocs_root}\\1/\\">\\1</a>"\n'
        f'ALIASES += "projectdocs{{2}}=<a href=\\"{projectdocs_root}\\1/\\">\\2</a>"\n'
    )


def _run_doxygen_profile(
    *,
    project_root: Path,
    configured_build: Path,
    base_config: str,
    doxygen_output: Path,
    checkout_version: str,
    profile: dict[str, object],
    profile_manifest: dict[str, object],
    profile_build: Path,
) -> Path:
    """Run Doxygen for one API profile and return its XML directory."""

    profile_name = str(profile["name"])
    profile_output = doxygen_output / "profiles" / profile_name
    public_include = _profile_public_include_tree(
        project_root, profile_build, doxygen_output, profile_name, profile_manifest
    )
    predefined = _profile_predefined(profile)

    clang_options = _clang_options(configured_build)
    clang_options.append(f"-I{str(public_include).replace(chr(92), '/')}")
    clang_options.extend(_profile_clang_defines(predefined))

    generated_config = profile_output / "Doxyfile"
    generated_config.parent.mkdir(parents=True, exist_ok=True)
    additions = [
        "",
        f"CLANG_OPTIONS += {_doxygen_list(clang_options)}",
        f'PROJECT_NUMBER = "{checkout_version}"',
        f"OUTPUT_DIRECTORY = {_doxygen_quote(profile_output)}",
        f"INPUT = {_doxygen_quote(public_include)}",
        f"STRIP_FROM_PATH = {_doxygen_quote(public_include)}",
        f"STRIP_FROM_INC_PATH = {_doxygen_quote(public_include)}",
    ]
    if predefined:
        additions.append(f"PREDEFINED += {_doxygen_list(predefined)}")
    generated_config.write_text(
        base_config + "\n" + "\n".join(additions) + "\n" + _projectdocs_aliases(),
        encoding="utf-8",
    )

    shutil.rmtree(profile_output / "xml", ignore_errors=True)
    executable = os.environ.get("BESA_DOXYGEN_EXECUTABLE", "doxygen")
    subprocess.run([executable, str(generated_config)], cwd=project_root, check=True)
    return profile_output / "xml"


def _xml_child_key(element: ET.Element) -> tuple[str, str, str]:
    return (
        element.tag,
        element.get("refid", "") or element.get("id", "") or element.get("kind", ""),
        _xml_text(element),
    )


def _merge_compound_xml(target_root: ET.Element, source_root: ET.Element) -> None:
    """Merge members/relationships from one profile's compound XML into another."""

    target = target_root.find("compounddef")
    source = source_root.find("compounddef")
    if target is None or source is None:
        return

    section_by_kind = {section.get("kind", ""): section for section in target.findall("sectiondef")}
    for source_section in source.findall("sectiondef"):
        kind = source_section.get("kind", "")
        target_section = section_by_kind.get(kind)
        if target_section is None:
            target.append(copy.deepcopy(source_section))
            section_by_kind[kind] = target[-1]
            continue
        existing = {
            member.get("id", "") or (member.findtext("name") or "") + _xml_text(member.find("argsstring"))
            for member in target_section.findall("memberdef")
        }
        for member in source_section.findall("memberdef"):
            key = member.get("id", "") or (member.findtext("name") or "") + _xml_text(member.find("argsstring"))
            if key not in existing:
                target_section.append(copy.deepcopy(member))
                existing.add(key)

    merge_tags = {
        "basecompoundref",
        "derivedcompoundref",
        "innerclass",
        "innernamespace",
        "innerfile",
        "innerdir",
        "includes",
        "includedby",
    }
    existing_children = {_xml_child_key(child) for child in target if child.tag in merge_tags}
    for child in source:
        if child.tag not in merge_tags:
            continue
        key = _xml_child_key(child)
        if key not in existing_children:
            target.append(copy.deepcopy(child))
            existing_children.add(key)


def _collect_profile_metadata(profile_xml: dict[str, Path]) -> dict[str, object]:
    """Collect per-profile entity availability and macro spellings before XML unioning."""

    availability: dict[str, list[str]] = {}
    define_variants: dict[str, dict[str, str]] = {}
    define_names: dict[str, str] = {}

    for profile, xml_directory in profile_xml.items():
        index = ET.parse(xml_directory / "index.xml").getroot()
        for compound in index.findall("compound"):
            refid = compound.get("refid", "")
            if refid:
                availability.setdefault(refid, []).append(profile)
            compound_xml = xml_directory / f"{refid}.xml"
            if not refid or not compound_xml.is_file():
                continue
            root = ET.parse(compound_xml).getroot()
            for member in root.findall(".//memberdef"):
                member_id = member.get("id", "")
                if member_id:
                    availability.setdefault(member_id, []).append(profile)
                if member.get("kind") != "define" or not member_id:
                    continue
                define_names[member_id] = member.findtext("name") or member_id
                value = _xml_text(member.find("initializer")) or "<empty>"
                define_variants.setdefault(member_id, {})[profile] = value

    return {
        "profiles": list(profile_xml),
        "availability": availability,
        "define_variants": define_variants,
        "define_names": define_names,
    }


def _merge_profile_xml(profile_xml: dict[str, Path], union_xml: Path) -> dict[str, object]:
    """Merge Doxygen XML from all API profiles into one Breathe/Exhale inventory."""

    if not profile_xml:
        raise RuntimeError("No API profiles were available for Doxygen")

    metadata = _collect_profile_metadata(profile_xml)
    first_xml = next(iter(profile_xml.values()))
    shutil.rmtree(union_xml, ignore_errors=True)
    shutil.copytree(first_xml, union_xml)

    index_roots = [ET.parse(path / "index.xml").getroot() for path in profile_xml.values()]
    union_index = copy.deepcopy(index_roots[0])
    compounds = {compound.get("refid", ""): compound for compound in union_index.findall("compound")}

    refids: set[str] = set(compounds)
    for source_index in index_roots[1:]:
        for source_compound in source_index.findall("compound"):
            refid = source_compound.get("refid", "")
            if not refid:
                continue
            refids.add(refid)
            target_compound = compounds.get(refid)
            if target_compound is None:
                target_compound = copy.deepcopy(source_compound)
                union_index.append(target_compound)
                compounds[refid] = target_compound
                continue
            existing_members = {member.get("refid", "") for member in target_compound.findall("member")}
            for member in source_compound.findall("member"):
                member_refid = member.get("refid", "")
                if member_refid and member_refid not in existing_members:
                    target_compound.append(copy.deepcopy(member))
                    existing_members.add(member_refid)

    ET.ElementTree(union_index).write(union_xml / "index.xml", encoding="utf-8", xml_declaration=True)

    for refid in sorted(refids):
        sources = [path / f"{refid}.xml" for path in profile_xml.values() if (path / f"{refid}.xml").is_file()]
        if not sources:
            continue
        merged = ET.parse(sources[0]).getroot()
        for source in sources[1:]:
            _merge_compound_xml(merged, ET.parse(source).getroot())
        ET.ElementTree(merged).write(union_xml / f"{refid}.xml", encoding="utf-8", xml_declaration=True)

    return metadata


def _write_profile_metadata(doxygen_output: Path, metadata: dict[str, object]) -> None:
    (doxygen_output / "api-profile-metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
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
    checkout_version = _project_version(project_root)
    doxygen_output = _doxygen_output_for(project_root)

    # Exhale generates files into the active Sphinx source directory. For current-checkout builds
    # this is an external staged copy; for multiversion builds it is sphinx-multiversion's checkout.
    # Remove stale output first so deleted/renamed API entities cannot survive an incremental build.
    shutil.rmtree(api_docs_directory / "generated", ignore_errors=True)

    # The source-location data file is generated after Exhale has emitted its program-listing pages.
    # Publish an empty placeholder first so historical/partial source trees still have every asset
    # named by html_js_files even if API post-processing later has nothing to record.
    source_locations_js = api_docs_directory / "_static" / "js" / "besa-api-source-locations.js"
    source_locations_js.parent.mkdir(parents=True, exist_ok=True)
    source_locations_js.write_text("window.BESA_API_SOURCE_LOCATIONS = {};\n", encoding="utf-8")

    doxygen_output.mkdir(parents=True, exist_ok=True)
    configured_build = _configured_build_for(project_root, doxygen_output)
    base_config = _configured_doxyfile(api_docs_directory, configured_build).read_text(
        encoding="utf-8"
    )
    catalog = _api_profile_catalog(project_root, doxygen_output, configured_build)
    profiles = catalog.get("profiles", [])
    if not isinstance(profiles, list) or not profiles:
        # Historical refs created before explicit profiles retain their previous single-build API.
        profiles = [{"name": "default", "features": catalog.get("active_features", []), "predefined": []}]

    profile_xml: dict[str, Path] = {}
    profile_manifests: dict[str, dict[str, object]] = {}
    primary_public_include: Path | None = None
    for profile in profiles:
        if not isinstance(profile, dict) or not profile.get("name"):
            continue
        profile_name = str(profile["name"])
        profile_build = doxygen_output / "profiles" / profile_name / "project-build"
        if profile_name == "default":
            profile_manifest = catalog
            profile_build = configured_build
        else:
            profile_manifest = _configure_api_discovery(
                project_root, profile_build, profile=profile_name
            )
            if profile_manifest is None:
                raise RuntimeError(f"API profile {profile_name!r} did not produce a BESA API manifest")
        profile_manifests[profile_name] = profile_manifest
        xml_directory = _run_doxygen_profile(
            project_root=project_root,
            configured_build=configured_build,
            base_config=base_config,
            doxygen_output=doxygen_output,
            checkout_version=checkout_version,
            profile=profile,
            profile_manifest=profile_manifest,
            profile_build=profile_build,
        )
        profile_xml[profile_name] = xml_directory
        if primary_public_include is None:
            primary_public_include = doxygen_output / "profiles" / profile_name / "public-include"

    metadata = _merge_profile_xml(profile_xml, doxygen_output / "xml")
    metadata["catalog"] = catalog
    metadata["profile_manifests"] = profile_manifests
    metadata["documentation_inputs"] = [
        {
            "path": str(path.relative_to(project_root)).replace(chr(92), "/"),
            "kind": "test-support",
            "api": "public",
            "feature": f"toolchain-{path.parent.name}",
        }
        for path in sorted(project_root.glob("test/base/*/include"))
        if path.is_dir()
    ]
    _write_profile_metadata(doxygen_output, metadata)
    if primary_public_include is None:
        raise RuntimeError("No API profile produced a public include tree")

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
    checkout_exhale_args["doxygenStripFromPath"] = str(primary_public_include)
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


def _function_display_signature(member: ET.Element) -> str:
    """Return a compact display signature for one Doxygen function member."""

    name = member.findtext("name") or ""
    parameters: list[str] = []
    for parameter in member.findall("param"):
        parameter_type = _xml_text(parameter.find("type"))
        array = _xml_text(parameter.find("array"))
        if parameter_type:
            parameters.append(f"{parameter_type}{array}")
    return f"{name}({', '.join(parameters)})"


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
            display = _function_display_signature(member)
            result.setdefault((namespace, name), []).append(
                (display, f"exhale_function_{member_refid}")
            )

    # Keep Doxygen/source order.  The combined overload page renders declarations in this same
    # order, which also keeps browser-side source metadata aligned with each declaration.
    for key, signatures in result.items():
        unique: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for signature in signatures:
            if signature in seen:
                continue
            seen.add(signature)
            unique.append(signature)
        result[key] = unique
    return result


_OPERATOR_DOCUMENT_NAMES = {
    "new": "new",
    "new[]": "new_array",
    "delete": "delete",
    "delete[]": "delete_array",
    "+": "plus",
    "-": "minus",
    "*": "multiply",
    "/": "divide",
    "%": "modulo",
    "^": "xor",
    "&": "bit_and",
    "|": "bit_or",
    "~": "bit_not",
    "!": "not",
    "=": "assign",
    "<": "less",
    ">": "greater",
    "+=": "plus_assign",
    "-=": "minus_assign",
    "*=": "multiply_assign",
    "/=": "divide_assign",
    "%=": "modulo_assign",
    "^=": "xor_assign",
    "&=": "bit_and_assign",
    "|=": "bit_or_assign",
    "<<": "shift_left",
    ">>": "shift_right",
    "<<=": "shift_left_assign",
    ">>=": "shift_right_assign",
    "==": "equal",
    "!=": "not_equal",
    "<=": "less_equal",
    ">=": "greater_equal",
    "<=>": "spaceship",
    "&&": "logical_and",
    "||": "logical_or",
    "++": "increment",
    "--": "decrement",
    ",": "comma",
    "->*": "arrow_star",
    "->": "arrow",
    "()": "call",
    "[]": "subscript",
}


def _overload_document_name(namespace: str, function: str) -> str:
    """Return a stable, operator-safe Sphinx document name for one overload set.

    A plain punctuation-stripping slug makes every symbolic operator collapse to ``operator``.
    Keep ordinary function URLs unchanged, but spell C++ operators explicitly so ``operator-``,
    ``operator+``, ``operator<=``, and friends always own different generated documents.
    """

    namespace_slug = re.sub(r"[^A-Za-z0-9]+", "_", namespace).strip("_").lower()
    function_slug = re.sub(r"[^A-Za-z0-9_]+", "_", function).strip("_").lower()

    if function.startswith("operator"):
        spelling = function[len("operator") :].strip()
        if spelling:
            operator_name = _OPERATOR_DOCUMENT_NAMES.get(spelling)
            if operator_name is None:
                # Keep unknown/future operator spellings distinct instead of silently collapsing
                # them. Hex code points are filesystem- and URL-safe and deterministic.
                operator_name = "code_" + "_".join(f"{ord(character):x}" for character in spelling)
            function_slug = f"operator_{operator_name}"

    slug = "_".join(part for part in (namespace_slug, function_slug) if part)
    return f"api_overload_{slug}"


def _function_directive_target(page: Path) -> str | None:
    """Return the Breathe target from one Exhale standalone function page."""

    directive = re.compile(r"^\s*\.\. doxygenfunction::\s*(?P<target>.+?)\s*$")
    for line in page.read_text(encoding="utf-8").splitlines():
        match = directive.match(line)
        if match is not None:
            return match.group("target")
    return None


def _rewrite_consolidated_function_references(
    generated: Path, captions: dict[str, str]
) -> None:
    """Give references to embedded overload labels explicit link text.

    Exhale's standalone function pages put each ``exhale_function_*`` label directly above a
    document heading, so generated ``:ref:`label``` links can borrow that heading as their caption.
    Consolidated family pages intentionally put the same labels immediately above Breathe
    directives instead.  The anchors remain valid, but there is no section title for Sphinx to use
    as an implicit caption.  Rewrite only those implicit references to carry the original overload
    signature explicitly; already-explicit references are left untouched.
    """

    if not captions:
        return

    implicit_reference = re.compile(r":ref:`(?P<label>exhale_function_[^`]+)`")
    for path in generated.glob("*.rst"):
        text = path.read_text(encoding="utf-8")

        def replace(match: re.Match[str]) -> str:
            label = match.group("label")
            caption = captions.get(label)
            if caption is None:
                return match.group(0)
            return f":ref:`{_rst_role_title(caption)} <{label}>`"

        rewritten = implicit_reference.sub(replace, text)
        if rewritten != text:
            path.write_text(rewritten, encoding="utf-8")


def _write_overload_pages(
    index_xml: Path, generated: Path
) -> dict[tuple[str, str], str]:
    """Consolidate every overloaded namespace function onto one canonical family page.

    Exhale normally creates one page per overload.  That makes a function family such as
    ``operator>`` or ``to_string`` an index of links followed by several almost-identical pages.
    Instead, preserve each overload's Exhale label, render its original ``doxygenfunction``
    directive directly on the family page, and remove the redundant standalone pages.  Existing
    ``:ref:`` links therefore keep resolving, but now land at the matching declaration inside the
    family page.
    """

    for stale in generated.glob("api_overload_*.rst"):
        stale.unlink()

    # Resolve labels before removing Exhale's standalone function documents.  Reading the exact
    # directive target from those pages is safer than reconstructing modern C++ signatures from
    # XML, especially for constrained templates and operators.
    label_documents = _generated_label_documents(generated)
    result: dict[tuple[str, str], str] = {}
    document_owners: dict[str, tuple[str, str]] = {}
    obsolete_pages: set[Path] = set()
    reference_captions: dict[str, str] = {}

    for (namespace, function), signatures in _namespace_function_signatures(index_xml).items():
        if len(signatures) < 2:
            continue

        document_name = _overload_document_name(namespace, function)
        owner = (namespace, function)
        previous_owner = document_owners.get(document_name)
        if previous_owner is not None and previous_owner != owner:
            raise RuntimeError(
                "API overload document-name collision: "
                f"{previous_owner!r} and {owner!r} both map to {document_name!r}"
            )
        document_owners[document_name] = owner

        declarations: list[tuple[str, str]] = []
        for display, label in signatures:
            source_document = label_documents.get(label)
            source_page = generated / f"{source_document}.rst" if source_document else None
            if source_page is None or not source_page.is_file():
                raise RuntimeError(
                    f"Cannot consolidate overload {label!r}: its generated Exhale page was not found"
                )
            target = _function_directive_target(source_page)
            if target is None:
                raise RuntimeError(
                    f"Cannot consolidate overload {label!r}: no doxygenfunction directive in "
                    f"{source_page.name!r}"
                )
            declarations.append((label, target))
            reference_captions[label] = display
            obsolete_pages.add(source_page)

        title = function
        lines = [title, "=" * len(title), ""]
        for label, target in declarations:
            lines.extend(
                [
                    f".. _{label}:",
                    "",
                    f".. doxygenfunction:: {target}",
                    "",
                ]
            )

        (generated / f"{document_name}.rst").write_text("\n".join(lines), encoding="utf-8")
        result[(namespace, function)] = document_name

    # Generated file and namespace pages often refer to Exhale function labels without explicit
    # link text.  Once those labels live beside Breathe directives on a family page, Sphinx cannot
    # infer a caption from a following heading, so make the signature explicit before deleting the
    # old standalone documents.
    _rewrite_consolidated_function_references(generated, reference_captions)

    for page in obsolete_pages:
        page.unlink()

    return result


_PROFILE_AVAILABILITY_BEGIN = ".. besa-profile-availability-begin"
_PROFILE_AVAILABILITY_END = ".. besa-profile-availability-end"


def _profile_display_name(profile: str) -> str:
    """Return a compact human-facing API profile name."""

    return profile.upper()


def _profile_reference_label(profile: str) -> str:
    """Return the stable label used by one profile on the API configuration page."""

    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", profile).strip("-").lower()
    return f"besa-api-profile-{slug or 'profile'}"


def _profile_reference(profile: str) -> str:
    """Return an RST link to one API profile's detailed configuration entry."""

    return f":ref:`{_profile_display_name(profile)} <{_profile_reference_label(profile)}>`"


def _profile_availability_block(refid: str, profiles: list[str]) -> str:
    """Return one small availability block for an API entity."""

    return "\n".join(
        [
            f"{_PROFILE_AVAILABILITY_BEGIN} {refid}",
            "",
            ".. rubric:: Availability",
            "",
            " · ".join(
                [
                    *(_profile_reference(profile) for profile in profiles),
                    ":doc:`API configuration </generated/api_configuration>`",
                ]
            ),
            "",
            f"{_PROFILE_AVAILABILITY_END} {refid}",
        ]
    )


def _profile_entity_documents(index_xml: Path, generated: Path) -> dict[str, str]:
    """Map Doxygen entity ids to their canonical generated documents."""

    labels = _generated_label_documents(generated)
    result: dict[str, str] = {}
    root = ET.parse(index_xml).getroot()

    def add(refid: str, label: str) -> None:
        document = labels.get(label)
        if refid and document:
            result.setdefault(refid, document)

    for compound in root.findall("compound"):
        kind = compound.get("kind", "")
        refid = compound.get("refid", "")
        qualified = compound.findtext("name") or ""
        if kind == "namespace" and qualified:
            label = "namespace_" + qualified.replace(":", "_").replace(" ", "_")
            add(refid, label)
        elif kind == "concept":
            label = re.sub(r"[^A-Za-z0-9_]+", "_", f"besa_concept_{refid}")
            add(refid, label)
        elif kind in {"class", "struct", "union", "enum"}:
            add(refid, f"exhale_{kind}_{refid}")

        for member in compound.findall("member"):
            member_kind = member.get("kind", "")
            member_refid = member.get("refid", "")
            if not member_kind or not member_refid:
                continue
            if member_kind == "concept":
                label = re.sub(r"[^A-Za-z0-9_]+", "_", f"besa_concept_{member_refid}")
            else:
                label = f"exhale_{member_kind}_{member_refid}"
            add(member_refid, label)

    return result


def _insert_overload_availability(text: str, refid: str, block: str) -> str:
    """Attach availability to one exact overload on a consolidated family page."""

    anchor = f".. _exhale_function_{refid}:"
    start = text.find(anchor)
    if start == -1:
        return text
    next_anchor = text.find("\n.. _exhale_function_", start + len(anchor))
    insertion = len(text) if next_anchor == -1 else next_anchor
    before = text[:insertion].rstrip()
    after = text[insertion:].lstrip("\n")
    result = before + "\n\n" + block + "\n"
    if after:
        result += "\n" + after
    return result


def _write_profile_availability_sections(doxygen_output: Path, generated: Path) -> None:
    """Annotate every generated API entity with the profiles in which it exists."""

    metadata_path = doxygen_output / "api-profile-metadata.json"
    index_xml = doxygen_output / "xml" / "index.xml"
    if not metadata_path.is_file() or not index_xml.is_file():
        return
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    profiles = [str(value) for value in metadata.get("profiles", [])]
    availability = metadata.get("availability", {})
    if not profiles or not isinstance(availability, dict):
        return

    documents = _profile_entity_documents(index_xml, generated)
    for refid, profile_values in availability.items():
        if not isinstance(profile_values, list):
            continue
        present = {str(value) for value in profile_values}
        available = [profile for profile in profiles if profile in present]
        if not available:
            continue
        document = documents.get(str(refid))
        if not document:
            continue
        page = generated / f"{document}.rst"
        if not page.is_file():
            continue

        block = _profile_availability_block(str(refid), available)
        text = page.read_text(encoding="utf-8")
        if document.startswith("api_overload_"):
            text = _insert_overload_availability(text, str(refid), block)
            page.write_text(text, encoding="utf-8")
            continue

        # Keep availability subordinate to the entity documentation but ahead of supplementary
        # inheritance/relationship/profile-variant sections when those are present.
        insertion = len(text)
        for marker in (
            _PROFILE_VARIANTS_BEGIN,
            _INHERITANCE_BEGIN,
            _RELATED_OPERATORS_BEGIN,
            _RELATED_FUNCTIONS_BEGIN,
        ):
            candidate = text.find(marker)
            if candidate != -1 and candidate < insertion:
                insertion = candidate
        before = text[:insertion].rstrip()
        after = text[insertion:].lstrip("\n")
        result = before + "\n\n" + block + "\n"
        if after:
            result += "\n" + after
        page.write_text(result, encoding="utf-8")


_PROFILE_VARIANTS_BEGIN = ".. besa-profile-variants-begin"
_PROFILE_VARIANTS_END = ".. besa-profile-variants-end"


def _write_profile_variant_sections(doxygen_output: Path, generated: Path) -> None:
    """Show profile-dependent macro spellings on the macro's canonical page."""

    metadata_path = doxygen_output / "api-profile-metadata.json"
    if not metadata_path.is_file():
        return
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    profiles = [str(value) for value in metadata.get("profiles", [])]
    variants = metadata.get("define_variants", {})
    if not isinstance(variants, dict):
        return

    labels = _generated_label_documents(generated)
    for refid, profile_values in variants.items():
        if not isinstance(profile_values, dict):
            continue
        values = {str(profile_values.get(profile, "<unavailable>")) for profile in profiles}
        if len(values) <= 1:
            continue
        document = labels.get(f"exhale_define_{refid}")
        if not document:
            continue
        page = generated / f"{document}.rst"
        if not page.is_file():
            continue

        text = page.read_text(encoding="utf-8")
        if _PROFILE_VARIANTS_BEGIN in text:
            before, remainder = text.split(_PROFILE_VARIANTS_BEGIN, 1)
            if _PROFILE_VARIANTS_END in remainder:
                _old, after = remainder.split(_PROFILE_VARIANTS_END, 1)
                text = before.rstrip() + "\n" + after.lstrip("\n")

        lines = [
            text.rstrip(),
            "",
            _PROFILE_VARIANTS_BEGIN,
            "",
            ".. rubric:: Definitions by API profile",
            "",
            ".. list-table::",
            "   :header-rows: 1",
            "   :widths: 20 80",
            "",
            "   * - Profile",
            "     - Definition",
        ]
        for profile in profiles:
            value = str(profile_values.get(profile, "<unavailable>"))
            escaped = value.replace("`", "\\`")
            lines.extend([f"   * - {profile}", f"     - ``{escaped}``"])
        lines.extend(["", _PROFILE_VARIANTS_END, ""])
        page.write_text("\n".join(lines), encoding="utf-8")


def _manifest_profile_features(catalog: dict[str, object]) -> dict[str, list[str]]:
    """Return declared API profile feature sets in manifest order."""

    result: dict[str, list[str]] = {}
    profiles = catalog.get("profiles", [])
    if not isinstance(profiles, list):
        return result
    for profile in profiles:
        if not isinstance(profile, dict) or not profile.get("name"):
            continue
        features = profile.get("features", [])
        result[str(profile["name"])] = (
            [str(value) for value in features] if isinstance(features, list) else []
        )
    return result


def _registration_identity(registration: dict[str, object]) -> tuple[str, ...]:
    """Return the build-directory-independent identity of one BESA API registration."""

    return tuple(
        str(registration.get(field) or "")
        for field in ("kind", "name", "path", "base", "language", "api")
    )


def _write_api_configuration_page(doxygen_output: Path, generated: Path) -> str | None:
    """Generate a human-readable explanation of the complete API configuration model."""

    metadata_path = doxygen_output / "api-profile-metadata.json"
    if not metadata_path.is_file():
        return None
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    profile_names = [str(value) for value in metadata.get("profiles", [])]
    catalog_value = metadata.get("catalog", {})
    catalog = catalog_value if isinstance(catalog_value, dict) else {}
    profile_manifests_value = metadata.get("profile_manifests", {})
    profile_manifests = (
        profile_manifests_value if isinstance(profile_manifests_value, dict) else {}
    )
    profile_features = _manifest_profile_features(catalog)
    if not profile_names:
        profile_names = list(profile_features)

    declared_value = catalog.get("declared_features", [])
    declared_features = (
        [str(value) for value in declared_value] if isinstance(declared_value, list) else []
    )
    if not declared_features:
        declared_features = sorted(
            {feature for features in profile_features.values() for feature in features}
        )
    active_value = catalog.get("active_features", [])
    active_features = (
        {str(value) for value in active_value} if isinstance(active_value, list) else set()
    )

    project_name = str(catalog.get("project") or project)
    lines = [
        "API configuration",
        "=================",
        "",
        "This page is generated from the BESA API manifests used to build this reference. The",
        "reference is the union of all declared API profiles; an entity's ``Availability`` field",
        "shows the profiles in which that declaration exists.",
        "",
        "Documentation model",
        "-------------------",
        "",
        ".. list-table::",
        "   :widths: 30 70",
        "",
        "   * - Project",
        f"     - ``{project_name}``",
        "   * - API profiles",
        "     - " + (" · ".join(_profile_reference(name) for name in profile_names) or "none"),
        "   * - Reference model",
        "     - Union of all registered API profiles",
        "   * - Manifest schema",
        f"     - ``{catalog.get('schema_version', 'unknown')}``",
        "",
        "Feature/profile matrix",
        "----------------------",
        "",
        ".. list-table::",
        "   :header-rows: 1",
        "",
        "   * - Feature",
        "     - Documentation build",
    ]
    for name in profile_names:
        lines.append(f"     - {_profile_reference(name)}")
    for feature in declared_features:
        lines.extend(
            [
                f"   * - ``{feature}``",
                f"     - {'yes' if feature in active_features else '—'}",
            ]
        )
        for name in profile_names:
            lines.append(
                f"     - {'yes' if feature in set(profile_features.get(name, [])) else '—'}"
            )

    lines.extend(["", "API profiles", "------------", ""])
    profile_declarations = {
        str(item.get("name")): item
        for item in catalog.get("profiles", [])
        if isinstance(item, dict) and item.get("name")
    } if isinstance(catalog.get("profiles", []), list) else {}
    for name in profile_names:
        declaration = profile_declarations.get(name, {})
        features = profile_features.get(name, [])
        predefined_value = declaration.get("predefined", []) if isinstance(declaration, dict) else []
        predefined = (
            [str(value) for value in predefined_value]
            if isinstance(predefined_value, list)
            else []
        )
        lines.extend(
            [
                f".. _{_profile_reference_label(name)}:",
                "",
                f".. rubric:: {_profile_display_name(name)}",
                "",
                "Features",
                "  " + (" · ".join(f"``{value}``" for value in features) or "none"),
                "",
                "Parser predefinitions",
                "  " + (" · ".join(f"``{value}``" for value in predefined) or "none"),
                "",
            ]
        )

    # Merge the same registration across all profile-specific manifests, retaining which profiles
    # selected it. This is the useful mapping from the declarative project model to API topology.
    registrations: dict[tuple[str, ...], dict[str, object]] = {}
    catalog_registrations = catalog.get("registrations", [])
    if isinstance(catalog_registrations, list):
        for item in catalog_registrations:
            if isinstance(item, dict):
                registrations.setdefault(_registration_identity(item), dict(item))
    selected_by_profile: dict[tuple[str, ...], list[str]] = {}
    for name in profile_names:
        manifest = profile_manifests.get(name, {})
        if not isinstance(manifest, dict):
            continue
        values = manifest.get("registrations", [])
        if not isinstance(values, list):
            continue
        for item in values:
            if not isinstance(item, dict):
                continue
            key = _registration_identity(item)
            registrations.setdefault(key, dict(item))
            if item.get("selected"):
                selected_by_profile.setdefault(key, []).append(name)

    lines.extend(
        [
            "Registered project inputs",
            "-------------------------",
            "",
            "These registrations come directly from the BESA project model. ``API`` describes",
            "whether the registration contributes to the public reference; ``Profiles`` shows",
            "which API-profile configurations select it.",
            "",
            ".. list-table::",
            "   :header-rows: 1",
            "",
            "   * - Name",
            "     - Kind",
            "     - Path",
            "     - API",
            "     - Profiles",
        ]
    )
    for key, registration in sorted(
        registrations.items(), key=lambda item: (str(item[1].get("path", "")), str(item[1].get("name", "")))
    ):
        selected = selected_by_profile.get(key, [])
        lines.extend(
            [
                f"   * - ``{registration.get('name', '')}``",
                f"     - ``{registration.get('kind', '')}``",
                f"     - ``{registration.get('path', '')}``",
                f"     - ``{registration.get('api', '')}``",
                "     - " + (" · ".join(_profile_reference(name) for name in selected) or "—"),
            ]
        )

    documentation_inputs = metadata.get("documentation_inputs", [])
    if isinstance(documentation_inputs, list) and documentation_inputs:
        lines.extend(
            [
                "",
                "Documentation-only API inputs",
                "-----------------------------",
                "",
                "The generated project currently exposes these developer-facing test-support headers in the API",
                "reference. They are staged by the documentation layer and are shown separately",
                "because they are not yet ordinary BESA project registrations.",
                "",
                ".. list-table::",
                "   :header-rows: 1",
                "",
                "   * - Path",
                "     - Required feature",
                "     - Profiles",
            ]
        )
        for item in documentation_inputs:
            if not isinstance(item, dict):
                continue
            feature = str(item.get("feature") or "")
            selected = [
                name for name in profile_names if feature in set(profile_features.get(name, []))
            ]
            lines.extend(
                [
                    f"   * - ``{item.get('path', '')}``",
                    f"     - ``{feature}``",
                    "     - " + (" · ".join(_profile_reference(name) for name in selected) or "—"),
                ]
            )

    document = "api_configuration"
    (generated / f"{document}.rst").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return document


_RELATED_OPERATORS_BEGIN = ".. besa-related-operators-begin"
_RELATED_OPERATORS_END = ".. besa-related-operators-end"


def _write_related_operator_sections(index_xml: Path, generated: Path) -> None:
    """Append links to matching non-member operators to class-like entity pages.

    Operators remain documented exactly once: standalone when unique, or on the canonical
    consolidated family page when overloaded.  Class/struct/union pages only gain contextual
    links to the exact ``exhale_function_*`` anchor for overloads whose parameter types refer to
    that documented type.  Ordinary free functions are deliberately ignored even when they take
    the type as an argument.
    """

    root = ET.parse(index_xml).getroot()
    labels = _generated_label_documents(generated)
    type_pages: dict[str, Path] = {}
    for compound in root.findall("compound"):
        kind = compound.get("kind", "")
        refid = compound.get("refid", "")
        if kind not in {"class", "struct", "union"} or not refid:
            continue
        document = labels.get(f"exhale_{kind}_{refid}")
        if document:
            page = generated / f"{document}.rst"
            if page.is_file():
                type_pages[refid] = page

    related: dict[str, list[tuple[str, str]]] = {refid: [] for refid in type_pages}
    seen: dict[str, set[str]] = {refid: set() for refid in type_pages}

    for compound in root.findall("compound"):
        if compound.get("kind") != "namespace":
            continue
        refid = compound.get("refid", "")
        compound_xml = index_xml.parent / f"{refid}.xml"
        if not refid or not compound_xml.is_file():
            continue

        compound_root = ET.parse(compound_xml).getroot()
        for member in compound_root.findall(".//memberdef[@kind='function']"):
            name = member.findtext("name") or ""
            member_refid = member.get("id", "")
            if not name.startswith("operator") or not member_refid:
                continue

            matching_types: set[str] = set()
            for parameter in member.findall("param"):
                for reference in parameter.findall(".//ref"):
                    type_refid = reference.get("refid", "")
                    if type_refid in type_pages:
                        matching_types.add(type_refid)

            if not matching_types:
                continue

            display = _function_display_signature(member)
            label = f"exhale_function_{member_refid}"
            for type_refid in matching_types:
                if member_refid in seen[type_refid]:
                    continue
                seen[type_refid].add(member_refid)
                related[type_refid].append((display, label))

    for type_refid, page in type_pages.items():
        entries = related[type_refid]
        if not entries:
            continue

        text = page.read_text(encoding="utf-8")
        if _RELATED_OPERATORS_BEGIN in text:
            before, remainder = text.split(_RELATED_OPERATORS_BEGIN, 1)
            if _RELATED_OPERATORS_END in remainder:
                _old, after = remainder.split(_RELATED_OPERATORS_END, 1)
                text = before.rstrip() + "\n" + after.lstrip("\n")

        lines = [
            text.rstrip(),
            "",
            _RELATED_OPERATORS_BEGIN,
            "",
            ".. rubric:: Related operators",
            "",
        ]
        for display, label in entries:
            lines.append(f"* :ref:`{_rst_role_title(display)} <{label}>`")
        lines.extend(["", _RELATED_OPERATORS_END, ""])
        page.write_text("\n".join(lines), encoding="utf-8")


_RELATED_FUNCTIONS_BEGIN = ".. besa-related-functions-begin"
_RELATED_FUNCTIONS_END = ".. besa-related-functions-end"
_RELATED_FUNCTION_MARKER = re.compile(
    r"^\s*//\s*BESA-API-RELATES-TO:\s*(?P<target>[A-Za-z_][A-Za-z0-9_:]*)\s*$"
)


_INHERITANCE_BEGIN = ".. besa-inheritance-begin"
_INHERITANCE_END = ".. besa-inheritance-end"


def _dot_label(value: str) -> str:
    """Escape text for one Graphviz quoted label."""

    return value.replace("\\", "\\\\").replace('"', '\\"')


def _compound_display_name(compound_root: ET.Element) -> str:
    """Return a compact class-like name, including template parameter names."""

    compounddef = compound_root.find("compounddef")
    if compounddef is None:
        return "type"

    qualified = _xml_text(compounddef.find("compoundname"))
    short = qualified.rsplit("::", 1)[-1] if qualified else "type"
    parameters: list[str] = []
    template_parameters = compounddef.find("templateparamlist")
    if template_parameters is not None:
        for parameter in template_parameters.findall("param"):
            name = _xml_text(parameter.find("declname"))
            if name:
                parameters.append(name)
    if parameters:
        return f"{short}<" + ", ".join(parameters) + ">"
    return short


def _compound_reference_display(
    reference: ET.Element,
    xml_directory: Path,
    cache: dict[str, str],
) -> str:
    """Return a compact display name for one Doxygen base/derived reference."""

    refid = reference.get("refid", "")
    if refid:
        cached = cache.get(refid)
        if cached is not None:
            return cached
        xml_path = xml_directory / f"{refid}.xml"
        if xml_path.is_file():
            cached = _compound_display_name(ET.parse(xml_path).getroot())
            cache[refid] = cached
            return cached

    value = _xml_text(reference)
    return value.rsplit("::", 1)[-1] if value else "type"


def _inheritance_graph_rst(
    compound_root: ET.Element,
    xml_directory: Path,
    display_cache: dict[str, str],
) -> list[str]:
    """Render one class/struct/union inheritance graph as RST Graphviz input."""

    compounddef = compound_root.find("compounddef")
    if compounddef is None:
        return []

    bases = list(compounddef.findall("basecompoundref"))
    derived = list(compounddef.findall("derivedcompoundref"))
    if not bases and not derived:
        return []

    current = _dot_label(_compound_display_name(compound_root))
    lines = [
        _INHERITANCE_BEGIN,
        "",
        "Inheritance",
        "-----------",
        "",
        ".. graphviz::",
        "",
        "   digraph inheritance {",
        "       rankdir=TB;",
        '       graph [bgcolor="transparent", pad="0.12", nodesep="0.4", ranksep="0.5"];',
        '       node [shape=box, style="rounded", fontname="sans-serif", fontsize=10];',
        '       edge [fontname="sans-serif", fontsize=9, arrowsize=0.7];',
        f'       current [label="{current}", penwidth=1.6];',
    ]

    for index, base in enumerate(bases):
        label = _dot_label(_compound_reference_display(base, xml_directory, display_cache))
        lines.append(f'       base_{index} [label="{label}"];')
        protection = _dot_label(base.get("prot", ""))
        attributes = f' [label="{protection}"]' if protection else ""
        lines.append(f"       base_{index} -> current{attributes};")

    for index, child in enumerate(derived):
        label = _dot_label(_compound_reference_display(child, xml_directory, display_cache))
        lines.append(f'       derived_{index} [label="{label}"];')
        protection = _dot_label(child.get("prot", ""))
        attributes = f' [label="{protection}"]' if protection else ""
        lines.append(f"       current -> derived_{index}{attributes};")

    lines.extend(["   }", "", _INHERITANCE_END, ""])
    return lines


def _remove_exhale_inheritance_block(text: str) -> str:
    """Remove Exhale's textual inheritance block that precedes the declaration."""

    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line != "Inheritance Relationships":
            continue
        directive = next(
            (
                candidate
                for candidate in range(index + 1, len(lines))
                if lines[candidate].startswith(".. doxygen")
            ),
            None,
        )
        if directive is None:
            break
        del lines[index:directive]
        while index < len(lines) and not lines[index] and index and not lines[index - 1]:
            del lines[index]
        break
    return "\n".join(lines) + "\n"


def _write_inheritance_graph_sections(index_xml: Path, generated: Path) -> None:
    """Replace Exhale's pre-declaration base list with a post-API inheritance graph."""

    root = ET.parse(index_xml).getroot()
    labels = _generated_label_documents(generated)
    xml_directory = index_xml.parent
    display_cache: dict[str, str] = {}

    for compound in root.findall("compound"):
        kind = compound.get("kind", "")
        refid = compound.get("refid", "")
        if kind not in {"class", "struct", "union"} or not refid:
            continue

        document = labels.get(f"exhale_{kind}_{refid}")
        compound_xml = xml_directory / f"{refid}.xml"
        if not document or not compound_xml.is_file():
            continue
        page = generated / f"{document}.rst"
        if not page.is_file():
            continue

        graph = _inheritance_graph_rst(
            ET.parse(compound_xml).getroot(), xml_directory, display_cache
        )
        text = _remove_exhale_inheritance_block(page.read_text(encoding="utf-8"))

        if _INHERITANCE_BEGIN in text and _INHERITANCE_END in text:
            before, remainder = text.split(_INHERITANCE_BEGIN, 1)
            _old, after = remainder.split(_INHERITANCE_END, 1)
            text = before.rstrip() + "\n" + after.lstrip("\n")

        if not graph:
            page.write_text(text, encoding="utf-8")
            continue

        insertion = len(text)
        for footer in (_RELATED_OPERATORS_BEGIN, _RELATED_FUNCTIONS_BEGIN):
            position = text.find(footer)
            if position != -1:
                insertion = min(insertion, position)

        before = text[:insertion].rstrip()
        after = text[insertion:].lstrip("\n")
        replacement = before + "\n\n" + "\n".join(graph).rstrip() + "\n"
        if after:
            replacement += "\n" + after.rstrip() + "\n"
        page.write_text(replacement, encoding="utf-8")


def _doxygen_source_file(index_xml: Path, source: str) -> Path | None:
    """Resolve one Doxygen ``location/@file`` back to the staged public header.

    BESA runs Doxygen over ``<doxygen-work>/public-include``.  The XML location may therefore be an
    absolute staged path or a path relative to that include root.  Keep this lookup local to the
    Doxygen work tree so multiversion builds always inspect the exact checkout/header that produced
    the XML rather than the current source checkout.
    """

    source_path = Path(source)
    if source_path.is_file():
        return source_path

    normalized = _normalized_source_path(source)
    staged_root = index_xml.parent.parent / "public-include"
    candidate = staged_root.joinpath(*PurePosixPath(normalized).parts)
    if candidate.is_file():
        return candidate

    matches = [
        path
        for path in staged_root.rglob(Path(normalized).name)
        if _normalized_source_path(str(path)).endswith(normalized)
    ]
    return matches[0] if len(matches) == 1 else None


def _function_explicit_related_types(index_xml: Path, member: ET.Element) -> list[str]:
    """Return BESA-explicit related type names for one namespace function.

    Standard Doxygen ``\\relates`` / ``\\relatesalso`` duplicates a free function into the related
    compound's XML.  That is useful for Doxygen's own HTML output but makes Exhale/Breathe see two
    indistinguishable copies of the same ``doxygenfunction`` directive.  BESA therefore uses an
    inert source comment immediately before a declaration instead::

        // BESA-API-RELATES-TO: semantic_version

    The marker has no C++ or Doxygen semantics, so the canonical function inventory remains unique.
    """

    location = member.find("location")
    if location is None:
        return []
    source = location.get("file", "")
    line_text = location.get("line", "")
    if not source or not line_text.isdigit():
        return []

    source_file = _doxygen_source_file(index_xml, source)
    if source_file is None:
        return []
    lines = source_file.read_text(encoding="utf-8").splitlines()
    declaration_index = int(line_text) - 1
    if declaration_index <= 0 or declaration_index > len(lines):
        return []

    targets: list[str] = []
    # The marker is intentionally local to the declaration.  Permit attributes and adjacent comment
    # lines between it and the function, but never search through a previous declaration/body.
    for raw in reversed(lines[max(0, declaration_index - 8) : declaration_index]):
        match = _RELATED_FUNCTION_MARKER.match(raw)
        if match:
            target = match.group("target")
            if target not in targets:
                targets.append(target)
            continue
        stripped = raw.strip()
        if not stripped:
            break
        if stripped.startswith("//") or (stripped.startswith("[[") and stripped.endswith("]]")):
            continue
        break

    targets.reverse()
    return targets


def _related_type_document_label(kind: str, refid: str) -> str:
    """Return the generated canonical label for one type-like Doxygen compound."""

    if kind == "concept":
        return re.sub(r"[^A-Za-z0-9_]+", "_", f"besa_concept_{refid}")
    return f"exhale_{kind}_{refid}"


def _write_related_function_sections(index_xml: Path, generated: Path) -> None:
    """Append explicitly related ordinary functions as links on type pages.

    Ordinary functions are never inferred from parameter types.  Authors opt in with the inert
    ``// BESA-API-RELATES-TO: <type>`` marker immediately before the function declaration.  This
    avoids Doxygen's duplicate-function ``\\relatesalso`` representation while preserving the same
    semantic intent.  Operators remain handled separately and automatically.
    """

    root = ET.parse(index_xml).getroot()
    labels = _generated_label_documents(generated)

    types: dict[str, tuple[str, str]] = {}
    for compound in root.findall("compound"):
        kind = compound.get("kind", "")
        refid = compound.get("refid", "")
        qualified = compound.findtext("name") or ""
        if kind in {"class", "struct", "union", "concept"} and refid and qualified:
            document = labels.get(_related_type_document_label(kind, refid))
            if document:
                types[qualified] = (document, refid)

        # Doxygen does not normally expose namespace enums as top-level ``compound`` entries in
        # ``index.xml``.  They are ``member kind="enum"`` records owned by the namespace.  Index
        # those member records as well so an explicit relation can target an enum page such as
        # ``vorlage::meta::release_type``.
        if kind != "namespace" or not qualified:
            continue
        for member in compound.findall("member"):
            member_kind = member.get("kind", "")
            member_refid = member.get("refid", "")
            member_name = member.findtext("name") or ""
            if member_kind not in {"enum", "concept"} or not member_refid or not member_name:
                continue
            member_qualified = f"{qualified}::{member_name}"
            document = labels.get(_related_type_document_label(member_kind, member_refid))
            if document:
                types[member_qualified] = (document, member_refid)

    related: dict[str, list[tuple[str, str]]] = {}
    for compound in root.findall("compound"):
        if compound.get("kind") != "namespace":
            continue
        namespace = compound.findtext("name") or ""
        refid = compound.get("refid", "")
        compound_xml = index_xml.parent / f"{refid}.xml"
        if not refid or not compound_xml.is_file():
            continue

        compound_root = ET.parse(compound_xml).getroot()
        for member in compound_root.findall(".//memberdef[@kind='function']"):
            name = member.findtext("name") or ""
            member_refid = member.get("id", "")
            if not member_refid or name.startswith("operator"):
                continue

            targets = _function_explicit_related_types(index_xml, member)
            if not targets:
                continue

            entry = (_function_display_signature(member), f"exhale_function_{member_refid}")
            for target in targets:
                qualified_target = target if "::" in target or not namespace else f"{namespace}::{target}"
                type_info = types.get(qualified_target)
                if type_info is None:
                    raise RuntimeError(
                        f"BESA-API-RELATES-TO target {target!r} on {namespace}::{name} was not found "
                        "as a generated class/struct/union/enum/concept"
                    )
                document, _type_refid = type_info
                bucket = related.setdefault(document, [])
                if entry not in bucket:
                    bucket.append(entry)

    for document, entries in related.items():
        page = generated / f"{document}.rst"
        if not page.is_file():
            continue

        text = page.read_text(encoding="utf-8")
        if _RELATED_FUNCTIONS_BEGIN in text:
            before, remainder = text.split(_RELATED_FUNCTIONS_BEGIN, 1)
            if _RELATED_FUNCTIONS_END in remainder:
                _old, after = remainder.split(_RELATED_FUNCTIONS_END, 1)
                text = before.rstrip() + "\n" + after.lstrip("\n")

        lines = [
            text.rstrip(),
            "",
            _RELATED_FUNCTIONS_BEGIN,
            "",
            ".. rubric:: Related functions",
            "",
        ]
        for display, label in entries:
            lines.append(f"* :ref:`{_rst_role_title(display)} <{label}>`")
        lines.extend(["", _RELATED_FUNCTIONS_END, ""])
        page.write_text("\n".join(lines), encoding="utf-8")


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
        ("Template Class ", "class"),
        ("Template Struct ", "struct"),
        ("Template Union ", "union"),
        ("Template Function ", "function"),
        ("Class ", "class"),
        ("Struct ", "struct"),
        ("Union ", "union"),
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
        "Union Documentation",
        "Enum Documentation",
        "Function Documentation",
        "Define Documentation",
        "Documentation",
    }
    explicit_reference = re.compile(
        r":ref:`(?P<title>(?:(?:Template )?(?:Class|Struct|Union|Function)|Enum|Define) .+?) "
        r"<(?P<target>exhale_[^`]+)>`"
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


def _api_global_macros(index_xml: Path, generated: Path) -> list[tuple[str, str]]:
    """Return documented preprocessor macros that live outside the C++ namespace hierarchy.

    Doxygen owns macros through ``file`` compounds rather than namespace compounds.  Consequently a
    namespace-only API index can make perfectly valid macro pages unreachable except through file
    pages and incidental cross-references.  Keep macros as a separate global API category instead
    of pretending that they are members of a C++ namespace.
    """

    root = ET.parse(index_xml).getroot()
    labels = _generated_label_documents(generated)
    entries: dict[tuple[str, str], tuple[str, str]] = {}

    for compound in root.findall("compound"):
        if compound.get("kind") != "file":
            continue
        for member in compound.findall("member"):
            if member.get("kind") != "define":
                continue
            name = member.findtext("name") or ""
            refid = member.get("refid", "")
            if not name or not refid:
                continue
            document = labels.get(f"exhale_define_{refid}")
            if not document:
                continue
            entries[(name, refid)] = (name, document)

    return sorted(entries.values(), key=lambda entry: entry[0].casefold())


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
        ":api-kind:`E` enum  ·  :api-kind:`K` concept  ·  :api-kind:`F` function  ·  "
        ":api-kind:`D` macro",
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
    """Build the namespace API synopsis plus non-namespace API categories."""

    text = _api_namespace_tree(
        index_xml,
        generated,
        overload_pages=overload_pages,
    ).rstrip()
    macros = _api_global_macros(index_xml, generated)
    if not macros:
        return text + "\n"

    lines = [text, "", "* **Macros**", ""]
    for name, document in macros:
        lines.append(
            f"  * :api-kind:`D` :doc:`{_rst_role_title(name)} </generated/{document}>`"
        )
        lines.append("")
    return "\n".join(lines)


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



def _normalized_source_path(value: str) -> str:
    """Normalize one Doxygen/Exhale source path for cross-checkout matching."""

    return value.replace("\\", "/").removeprefix("./").rstrip("/")


def _program_listing_source_file(doxygen_output: Path, location: str) -> Path | None:
    """Resolve an Exhale program-listing location to the staged public source file.

    Program listings are presentation of source, not part of the merged semantic API model.  Read
    them from the staged public include trees so whitespace, comments, preprocessor branches, and
    portability macros remain exactly as written even when the Doxygen XML came from several API
    profiles and was round-tripped through ElementTree.
    """

    normalized = _normalized_source_path(location)
    direct = Path(location)
    if direct.is_file():
        return direct

    marker = "/public-include/"
    if marker in normalized:
        normalized = normalized.split(marker, 1)[1]
    relative = Path(normalized.lstrip("/"))

    roots = [doxygen_output / "public-include"]
    roots.extend(sorted(doxygen_output.glob("profiles/*/public-include")))
    roots = [root for root in roots if root.is_dir()]

    for root in roots:
        candidate = root / relative
        if candidate.is_file():
            return candidate

    # Historical Doxygen/Exhale versions can record a longer path than the configured
    # STRIP_FROM_PATH. Match by suffix as a compatibility fallback, but only when unambiguous.
    matches: list[Path] = []
    for root in roots:
        for candidate in root.rglob(relative.name):
            if not candidate.is_file():
                continue
            candidate_relative = _normalized_source_path(str(candidate.relative_to(root)))
            if normalized.endswith(candidate_relative) or candidate_relative.endswith(normalized):
                matches.append(candidate)
    unique = sorted(set(matches))
    return unique[0] if len(unique) == 1 else None


def _replace_program_listing_code(page: Path, source: Path) -> None:
    """Replace Exhale's Doxygen-derived listing with the literal staged source file."""

    lines = page.read_text(encoding="utf-8").splitlines()
    directive_index = next(
        (index for index, line in enumerate(lines) if line.lstrip().startswith(".. code-block::")),
        None,
    )
    if directive_index is None:
        return

    directive = lines[directive_index]
    directive_indent = directive[: len(directive) - len(directive.lstrip())]
    content_indent = directive_indent + "   "

    # A code-block ends at the next non-empty line that returns to the directive's indentation.
    block_end = directive_index + 1
    while block_end < len(lines):
        line = lines[block_end]
        if not line or line.startswith(content_indent):
            block_end += 1
            continue
        break

    source_lines = source.read_text(encoding="utf-8").splitlines()
    replacement = [directive, f"{content_indent}:linenos:", ""]
    replacement.extend(f"{content_indent}{line}" for line in source_lines)

    page.write_text(
        "\n".join([*lines[:directive_index], *replacement, *lines[block_end:]]) + "\n",
        encoding="utf-8",
    )


def _restore_program_listings_from_sources(doxygen_output: Path, generated: Path) -> None:
    """Make every Exhale program listing a faithful rendering of its staged source file."""

    location_pattern = re.compile(r"\(``(?P<location>[^`]+)``\)")
    for page in sorted(generated.glob("program_listing_*.rst")):
        head = "\n".join(page.read_text(encoding="utf-8").splitlines()[:24])
        match = location_pattern.search(head)
        if match is None:
            continue
        source = _program_listing_source_file(doxygen_output, match.group("location"))
        if source is not None:
            _replace_program_listing_code(page, source)


def _program_listing_documents(generated: Path) -> dict[str, str]:
    """Return source-path -> Exhale program-listing document mappings.

    Exhale records the original file location in each generated program-listing page.  Read that
    rather than reproducing Exhale's filename sanitization, which also has a hash fallback for very
    long paths. Ensure line numbers are enabled so source links can target ``#L123``.
    """

    result: dict[str, str] = {}
    location_pattern = re.compile(r"\(``(?P<location>[^`]+)``\)")
    for page in sorted(generated.glob("program_listing_*.rst")):
        lines = page.read_text(encoding="utf-8").splitlines()
        changed = False

        for index, line in enumerate(lines):
            if not line.lstrip().startswith(".. code-block::"):
                continue
            option_indent = line[: len(line) - len(line.lstrip())] + "   "
            option_end = index + 1
            has_linenos = False
            while option_end < len(lines) and lines[option_end].startswith(option_indent + ":"):
                if lines[option_end].strip() == ":linenos:":
                    has_linenos = True
                    break
                option_end += 1
            if not has_linenos:
                lines.insert(index + 1, f"{option_indent}:linenos:")
                changed = True
            break

        head = "\n".join(lines[:24])
        location_match = location_pattern.search(head)
        if location_match:
            result[_normalized_source_path(location_match.group("location"))] = page.stem

        if changed:
            page.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return result


def _resolve_program_listing(source: str, listings: dict[str, str]) -> tuple[str, str] | None:
    """Resolve a Doxygen source path to an Exhale program listing without guessing filenames."""

    normalized = _normalized_source_path(source)
    direct = listings.get(normalized)
    if direct:
        return normalized, direct

    matches = [
        (path, document)
        for path, document in listings.items()
        if normalized.endswith(f"/{path}") or path.endswith(f"/{normalized}")
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _function_qualifiers(member: ET.Element) -> list[str]:
    """Return function properties from Doxygen XML rather than rendered Sphinx text.

    Breathe intentionally normalizes some C++ declarations while rendering them.  In particular,
    leading specifiers such as ``constexpr`` may disappear from the visible signature even though
    Doxygen recorded them correctly.  Keep the presentation metadata tied to the XML model so the
    properties row remains complete on standalone and consolidated overload pages alike.
    """

    declaration_text = " ".join(
        value
        for value in (
            _xml_text(member.find("type")),
            _xml_text(member.find("definition")),
        )
        if value
    )
    args = _xml_text(member.find("argsstring"))
    qualifiers: list[str] = []

    def add(value: str) -> None:
        if value and value not in qualifiers:
            qualifiers.append(value)

    for qualifier in ("inline", "constexpr", "consteval", "static", "explicit", "friend"):
        if member.get(qualifier) == "yes" or re.search(
            rf"\b{re.escape(qualifier)}\b", declaration_text
        ):
            add(qualifier)

    if member.get("virt") in {"virtual", "pure-virtual"} or re.search(
        r"\bvirtual\b", declaration_text
    ):
        add("virtual")

    if member.get("const") == "yes" or re.search(r"\)\s*const\b", args):
        add("const")
    if member.get("volatile") == "yes" or re.search(r"\)\s*(?:const\s+)?volatile\b", args):
        add("volatile")

    refqual = member.get("refqual", "")
    if refqual in {"lvalue", "&"}:
        add("&")
    elif refqual in {"rvalue", "&&"}:
        add("&&")
    else:
        suffix = re.search(r"\)\s*(?:const\s+)?(?:volatile\s+)?(&&|&)\b", args)
        if suffix is not None:
            add(suffix.group(1))

    noexcept = re.search(r"\bnoexcept(?:\s*\([^)]*\))?", args)
    if noexcept is not None:
        add(noexcept.group(0))
    if re.search(r"\boverride\b", args):
        add("override")
    if re.search(r"\bfinal\b", args):
        add("final")

    return qualifiers


def _source_location(
    element: ET.Element,
    listings: dict[str, str],
    *,
    body_kind: str = "Implementation",
    file_kind: str = "Declaration",
) -> dict[str, object] | None:
    """Return the best local source-listing location for one Doxygen entity."""

    location = element.find("location")
    if location is None:
        return None

    candidates = [
        (body_kind, location.get("bodyfile", ""), location.get("bodystart", "")),
        (file_kind, location.get("file", ""), location.get("line", "")),
    ]
    for kind, source, line_text in candidates:
        if not source or not line_text.isdigit():
            continue
        resolved = _resolve_program_listing(source, listings)
        if resolved is None:
            continue
        display_file, document = resolved
        line = int(line_text)
        if line <= 0:
            continue
        return {
            "kind": kind,
            "file": display_file,
            "line": line,
            "href": f"{document}.html#L{line}",
        }
    return None


def _generated_label_documents(generated: Path) -> dict[str, str]:
    """Map generated labels to their document stems.

    Exhale's canonical entity label normally lives near the top of a standalone document.  A
    consolidated overload page is the deliberate exception: it preserves one Exhale label beside
    every embedded declaration, so scan those family pages in full without treating arbitrary
    nested labels on other generated pages as canonical document owners.
    """

    result: dict[str, str] = {}
    for page in generated.glob("*.rst"):
        lines = page.read_text(encoding="utf-8").splitlines()
        candidates = lines if page.name.startswith("api_overload_") else lines[:16]
        for line in candidates:
            match = re.match(r"^\.\. _([^:]+):$", line)
            if match:
                result[match.group(1)] = page.stem
    return result


def _api_source_locations(
    index_xml: Path, generated: Path, *, listings: dict[str, str] | None = None
) -> dict[str, object]:
    """Build per-page source metadata for Breathe-rendered API entities.

    Class pages contain many member functions inside a single ``doxygenclass`` / ``doxygenstruct``
    directive, so function metadata is grouped by function name and kept in Doxygen source order.
    The owning class/struct definition is also recorded so its declaration box can link to the
    corresponding source-listing line.
    """

    if listings is None:
        listings = _program_listing_documents(generated)
    if not listings:
        return {}

    labels = _generated_label_documents(generated)
    root = ET.parse(index_xml).getroot()
    result: dict[str, dict[str, object]] = {}

    def page_for(document: str) -> dict[str, object]:
        return result.setdefault(document, {"functions": {}, "symbols": {}})

    def add_function(document: str, name: str, metadata: dict[str, object] | None) -> None:
        """Keep the legacy name/occurrence map as a fallback for older rendered markup."""

        page = page_for(document)
        functions = page.setdefault("functions", {})
        assert isinstance(functions, dict)
        functions.setdefault(name, []).append(metadata)

    def add_function_symbol(
        document: str, member: ET.Element, metadata: dict[str, object] | None
    ) -> None:
        """Record one function by its stable Doxygen member id.

        Breathe emits the Doxygen member id as a ``span.target`` inside the rendered signature.
        Using that identity avoids positional overload matching, which becomes especially fragile
        once several standalone Exhale pages are consolidated onto one function-family page.
        """

        member_refid = member.get("id", "")
        if not member_refid:
            return
        symbol: dict[str, object] = {}
        if metadata is not None:
            symbol["source"] = metadata
        qualifiers = _function_qualifiers(member)
        if qualifiers:
            symbol["qualifiers"] = qualifiers
        if not symbol:
            return
        page = page_for(document)
        symbols = page.setdefault("symbols", {})
        assert isinstance(symbols, dict)
        symbols[member_refid] = symbol

    # Compound API entities own their standalone page. Concepts use the custom page emitted by
    # _write_concept_pages(); the remaining kinds use Exhale's normal compound labels. Templates
    # retain their class/struct/union Doxygen kind, so no template-specific XML kind is required.
    for compound in root.findall("compound"):
        kind = compound.get("kind", "")
        if kind not in {"class", "struct", "union", "concept"}:
            continue
        refid = compound.get("refid", "")
        if not refid:
            continue
        if kind == "concept":
            document = _concept_document_name(refid)
        else:
            document = labels.get(f"exhale_{kind}_{refid}")
        compound_xml = index_xml.parent / f"{refid}.xml"
        if not document or not compound_xml.is_file():
            continue
        compound_root = ET.parse(compound_xml).getroot()
        compounddef = compound_root.find("compounddef")
        if compounddef is not None:
            entity_source = _source_location(
                compounddef,
                listings,
                body_kind="Definition",
                file_kind="Definition",
            )
            if entity_source is not None:
                page_for(document)["entity"] = entity_source

        # Methods, constructors, operators, conversion operators, and function templates all remain
        # function members in Doxygen XML and are matched in source order on the owning page.
        for member in compound_root.findall(".//memberdef[@kind='function']"):
            name = member.findtext("name") or ""
            metadata = _source_location(member, listings)
            if name:
                # Preserve overload positions even when one declaration has no local listing.
                # Browser-side occurrence matching remains as a compatibility fallback, while the
                # stable member-id map handles current Breathe output exactly.
                add_function(document, name, metadata)
                add_function_symbol(document, member, metadata)

    # Free functions have standalone Exhale pages identified directly by the Doxygen member refid.
    for compound in root.findall("compound"):
        if compound.get("kind") != "namespace":
            continue
        refid = compound.get("refid", "")
        compound_xml = index_xml.parent / f"{refid}.xml"
        if not refid or not compound_xml.is_file():
            continue
        compound_root = ET.parse(compound_xml).getroot()
        for member in compound_root.findall(".//memberdef[@kind='function']"):
            member_refid = member.get("id", "")
            name = member.findtext("name") or ""
            document = labels.get(f"exhale_function_{member_refid}")
            metadata = _source_location(
                member,
                listings,
                body_kind="Definition",
                file_kind="Declaration",
            )
            if document and name:
                # Keep every overload position even if Doxygen cannot map one source path locally.
                add_function(document, name, metadata)
                add_function_symbol(document, member, metadata)

    # Exhale gives leaf entities their own pages. Do not duplicate Exhale's supported-kind list:
    # for every non-function Doxygen member, simply look for the label Exhale would have emitted.
    # This covers enums, typedefs / C++ using aliases, variables/constants, defines/macros, and any
    # additional member kind supported by the installed Exhale version. Enum values remain part of
    # their owning enum declaration rather than separate standalone pages.
    for compound in root.findall("compound"):
        refid = compound.get("refid", "")
        compound_xml = index_xml.parent / f"{refid}.xml"
        if not refid or not compound_xml.is_file():
            continue
        compound_root = ET.parse(compound_xml).getroot()
        for member in compound_root.findall(".//memberdef"):
            member_kind = member.get("kind", "")
            member_refid = member.get("id", "")
            if not member_kind or not member_refid or member_kind == "function":
                continue
            document = labels.get(f"exhale_{member_kind}_{member_refid}")
            if not document:
                continue
            metadata = _source_location(
                member,
                listings,
                body_kind="Definition",
                file_kind="Definition",
            )
            if metadata is not None:
                page_for(document)["entity"] = metadata

    return result


def _write_api_source_locations(app, index_xml: Path, generated: Path) -> None:
    """Publish API source metadata for links into literal source-backed program listings."""

    listings = _program_listing_documents(generated)
    metadata = _api_source_locations(index_xml, generated, listings=listings)
    target = Path(app.srcdir).resolve() / "_static" / "js" / "besa-api-source-locations.js"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "window.BESA_API_SOURCE_LOCATIONS = "
        + json.dumps(metadata, indent=2, sort_keys=True)
        + ";\nwindow.BESA_API_PROGRAM_LISTING_LINES = {};\n",
        encoding="utf-8",
    )


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

    _restore_program_listings_from_sources(index_xml.parent.parent, generated)
    _mark_template_specializations_no_link(index_xml, generated)
    _neutralize_deduction_guide_pages(index_xml, generated)
    _simplify_unique_function_directives(index_xml, generated)
    _simplify_generated_entity_pages(generated)
    _write_profile_variant_sections(index_xml.parent.parent, generated)
    concept_documents = _write_concept_pages(index_xml, generated)

    overload_pages = _write_overload_pages(index_xml, generated)
    _write_related_operator_sections(index_xml, generated)
    _write_related_function_sections(index_xml, generated)
    _write_inheritance_graph_sections(index_xml, generated)
    # Generate source metadata after overload consolidation so every overload label maps to the
    # canonical family document rather than to a standalone page that has just been removed.
    _write_api_source_locations(app, index_xml, generated)
    overview = generated / "api_namespace_overview.rst.include"
    overview.write_text(
        _api_namespace_overview(index_xml, generated, overload_pages),
        encoding="utf-8",
    )
    _rewrite_namespace_pages(index_xml, generated, overload_pages)
    _write_profile_availability_sections(index_xml.parent.parent, generated)
    api_configuration_document = _write_api_configuration_page(index_xml.parent.parent, generated)

    documents = [
        document
        for document in _unabridged_documents(unabridged)
        if (generated / document).is_file()
    ]
    documents.extend(document for document in concept_documents if document not in documents)
    if api_configuration_document and f"{api_configuration_document}.rst" not in documents:
        documents.append(f"{api_configuration_document}.rst")
    documents.extend(
        path.name for path in sorted(generated.glob("api_overload_*.rst")) if path.name not in documents
    )

    merged_landing = "generated/api_landing.rst.include" in index_source.read_text(encoding="utf-8")
    lines = [
        ":doc:`API configuration </generated/api_configuration>` explains the feature/profile",
        "matrix, public API inputs, parser predefinitions, and how this combined reference is built.",
        "",
        "API hierarchy",
        "-------------",
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


def _api_sidebar_tree(app) -> list[dict[str, object]]:
    """Return a recursive namespace/entity model for the global API outline.

    Namespace names are displayed locally (``detail`` below ``vorlage`` rather than repeatedly as
    ``vorlage::detail``), while every namespace name remains a normal navigation link.  The template
    gives namespaces a separate disclosure button so expanding the outline never hijacks that link.
    """

    cached = getattr(app, "_besa_api_sidebar_tree", None)
    if cached is not None:
        return cached

    generated = Path(app.srcdir).resolve() / "generated"
    xml_directory = Path(app.config.breathe_projects[project])
    index_xml = xml_directory / "index.xml"
    if not generated.is_dir() or not index_xml.is_file():
        app._besa_api_sidebar_tree = []
        return []

    root = ET.parse(index_xml).getroot()
    compounds = list(root.findall("compound"))
    labels = _generated_label_documents(generated)
    namespace_names = {
        name
        for compound in compounds
        if compound.get("kind") == "namespace"
        if (name := compound.findtext("name"))
    }
    function_counts = _namespace_function_counts(index_xml)
    class_like = _class_like_names(index_xml)

    markers = {
        "class": "C",
        "struct": "S",
        "union": "U",
        "enum": "E",
        "concept": "K",
        "typedef": "T",
        "variable": "V",
        "define": "D",
        "function": "F",
    }

    def document_for_label(label: str) -> str:
        stem = labels.get(label, "")
        return f"generated/{stem}" if stem else ""

    def namespace_document(namespace: str, refid: str) -> str:
        direct = generated / f"{refid}.rst"
        if refid and direct.is_file():
            return f"generated/{direct.stem}"
        label = "namespace_" + namespace.replace(":", "_").replace(" ", "_")
        return document_for_label(label)

    def compound_document(kind: str, refid: str) -> str:
        if kind == "concept":
            label = re.sub(r"[^A-Za-z0-9_]+", "_", f"besa_concept_{refid}")
            return document_for_label(label)
        return document_for_label(f"exhale_{kind}_{refid}")

    nodes: dict[str, dict[str, object]] = {}
    for compound in compounds:
        if compound.get("kind") != "namespace":
            continue
        namespace = compound.findtext("name") or ""
        refid = compound.get("refid", "")
        document = namespace_document(namespace, refid)
        if not namespace or not document:
            continue
        nodes[namespace] = {
            "name": namespace.rsplit("::", 1)[-1],
            "qualified_name": namespace,
            "document": document,
            "children": [],
            "entities": [],
            "documents": (),
            "dom_id": "besa-api-outline-" + re.sub(r"[^A-Za-z0-9_-]+", "-", namespace),
        }

    def add_entity(
        namespace: str,
        *,
        kind: str,
        name: str,
        document: str,
    ) -> None:
        node = nodes.get(namespace)
        marker = markers.get(kind)
        if node is None or marker is None or not name or not document:
            return
        entities = node["entities"]
        assert isinstance(entities, list)
        if any(
            entity["kind"] == kind and entity["name"] == name and entity["document"] == document
            for entity in entities
        ):
            return
        entities.append(
            {
                "kind": kind,
                "marker": marker,
                "name": f"{name}()" if kind == "function" else name,
                "document": document,
            }
        )

    # Compound entities are represented separately from namespace members in Doxygen's index.
    for compound in compounds:
        kind = compound.get("kind", "")
        if kind not in {"class", "struct", "union", "concept"}:
            continue
        qualified = compound.findtext("name") or ""
        refid = compound.get("refid", "")
        if "::" not in qualified or not refid:
            continue
        namespace, short_name = qualified.rsplit("::", 1)
        if namespace not in nodes:
            continue
        add_entity(
            namespace,
            kind=kind,
            name=short_name,
            document=compound_document(kind, refid),
        )

    # Leaf entities are namespace members. Collapse overloads to one sidebar entry and link that
    # entry to the compact overload page generated earlier during builder-inited.
    for compound in compounds:
        if compound.get("kind") != "namespace":
            continue
        namespace = compound.findtext("name") or ""
        if namespace not in nodes:
            continue
        seen_functions: set[str] = set()
        for member in compound.findall("member"):
            kind = member.get("kind", "")
            if kind not in {"enum", "concept", "typedef", "variable", "define", "function"}:
                continue
            name = member.findtext("name") or ""
            refid = member.get("refid", "")
            qualified = f"{namespace}::{name}" if name else ""
            if not name or not refid:
                continue
            if kind == "function" and qualified in class_like:
                # Doxygen also reports class template deduction guides as namespace functions.
                continue
            if kind == "function":
                if name in seen_functions:
                    continue
                seen_functions.add(name)
                if function_counts.get(qualified, 0) > 1:
                    overload_document = _overload_document_name(namespace, name)
                    overload_path = generated / f"{overload_document}.rst"
                    document = (
                        f"generated/{overload_document}" if overload_path.is_file() else ""
                    )
                else:
                    document = document_for_label(f"exhale_function_{refid}")
            elif kind == "concept":
                label = re.sub(r"[^A-Za-z0-9_]+", "_", f"besa_concept_{refid}")
                document = document_for_label(label)
            else:
                document = document_for_label(f"exhale_{kind}_{refid}")
            add_entity(namespace, kind=kind, name=name, document=document)

    roots: list[dict[str, object]] = []
    for namespace, node in nodes.items():
        parent = namespace.rsplit("::", 1)[0] if "::" in namespace else ""
        if parent in nodes:
            children = nodes[parent]["children"]
            assert isinstance(children, list)
            children.append(node)
        else:
            roots.append(node)

    def finalize(node: dict[str, object]) -> set[str]:
        children = node["children"]
        entities = node["entities"]
        assert isinstance(children, list)
        assert isinstance(entities, list)
        children.sort(key=lambda child: str(child["name"]).casefold())
        entities.sort(key=lambda entity: (str(entity["name"]).casefold(), str(entity["kind"])))

        documents = {str(node["document"])}
        documents.update(str(entity["document"]) for entity in entities)
        for child in children:
            documents.update(finalize(child))
        node["documents"] = tuple(sorted(documents))
        return documents

    roots.sort(key=lambda node: str(node["name"]).casefold())
    for root_node in roots:
        finalize(root_node)

    api_configuration = generated / "api_configuration.rst"
    if api_configuration.is_file():
        roots.insert(
            0,
            {
                "name": "API configuration",
                "qualified_name": "API configuration",
                "document": "generated/api_configuration",
                "children": [],
                "entities": [],
                "documents": ("generated/api_configuration",),
                "dom_id": "besa-api-outline-configuration",
                "group": True,
            },
        )

    macros = _api_global_macros(index_xml, generated)
    if macros:
        macro_entities = [
            {
                "kind": "define",
                "marker": "D",
                "name": name,
                "document": f"generated/{document}",
            }
            for name, document in macros
        ]
        roots.append(
            {
                "name": "Macros",
                "qualified_name": "Macros",
                "document": "",
                "children": [],
                "entities": macro_entities,
                "documents": tuple(sorted(str(entity["document"]) for entity in macro_entities)),
                "dom_id": "besa-api-outline-macros",
                "group": True,
            }
        )

    app._besa_api_sidebar_tree = roots
    return roots


def _api_sidebar_context(app, pagename, _templatename, context, _doctree) -> None:
    """Expose the recursive API outline to the custom PyData sidebar template."""

    context["besa_api_sidebar_tree"] = _api_sidebar_tree(app)
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
