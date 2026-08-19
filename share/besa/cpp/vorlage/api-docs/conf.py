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
exclude_patterns: list[str] = []

html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "navbar_align": "left",
    "navbar_end": ["project-links.html", "theme-switcher", "navbar-icon-links"],
    "primary_sidebar_end": ["versioning.html"],
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
    "kindsWithContentsDirectives": ["namespace", "class", "struct", "file"],
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
    base_config = (api_docs_directory / "Doxyfile").read_text(encoding="utf-8")
    generated_config = doxygen_output / "Doxyfile"
    generated_config.write_text(
        base_config
        + "\n"
        + f'PROJECT_NUMBER = "{checkout_version}"\n'
        + f"OUTPUT_DIRECTORY = {_doxygen_quote(doxygen_output)}\n"
        + f"INPUT = {_doxygen_quote(project_root / 'src')}\n"
        + f"STRIP_FROM_PATH = {_doxygen_quote(project_root)}\n",
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
    checkout_exhale_args["doxygenStripFromPath"] = str(project_root)
    app.config.exhale_args = checkout_exhale_args


def setup(app) -> None:
    """Generate checkout-specific XML before Exhale expands it into Sphinx pages."""

    # Sphinx invokes event listeners in ascending priority. Exhale uses builder-inited too, so run
    # before the normal extension priority (500).
    app.connect("builder-inited", _prepare_api, priority=100)
