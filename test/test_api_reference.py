# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

API_REFERENCE_ROOT = Path(__file__).resolve().parents[1] / "share" / "besa" / "cpp" / "cmake" / "userdocs"
if str(API_REFERENCE_ROOT) not in sys.path:
    sys.path.insert(0, str(API_REFERENCE_ROOT))

from api_reference.clang_backend import extract_cpp_graph
from api_reference.cpp_backend import _configuration_name, _variant_predefines
from api_reference.html_renderer import render_html_site
from api_reference.model import ApiEntity, ApiGraph, ApiParameter, ApiSignature, merge_graphs, stable_entity_id
from api_reference.python_backend import build_python_graph
from api_reference.render import entity_document
from api_reference.rust_backend import build_rust_graph


def test_cpp_semantic_profiles_merge_conditional_api(tmp_path: Path) -> None:
    clang = shutil.which("clang++") or shutil.which("clang")
    if clang is None:
        pytest.skip("Clang is required for the semantic API backend")

    include = tmp_path / "include"
    include.mkdir()
    (include / "dice.hpp").write_text(
        """#pragma once
#ifdef USE_CUDA
/// Active backend.
#define DICE_BACKEND \"cuda\"
namespace dice { struct cuda_view {}; void foo(cuda_view); }
#else
/// Active backend.
#define DICE_BACKEND \"cpu\"
namespace dice { struct cpu_view {}; void foo(cpu_view); }
#endif
class visible { public: void yes(); private: void no(); };
""",
        encoding="utf-8",
    )

    graphs = []
    for variant, predefines in (("cpu", []), ("cuda", ["USE_CUDA=1"])):
        graph = extract_cpp_graph(
            project="dice",
            version="main",
            project_root=tmp_path,
            build_directory=tmp_path / "build",
            public_roots=[include],
            profile_name=variant,
            predefines=predefines,
            clang_executable=clang,
            work_directory=tmp_path / "work" / variant,
        )
        graphs.append((variant, graph))

    merged = merge_graphs(graphs, project="dice", version="main", language="cpp")
    foo = merged.entities[stable_entity_id("cpp", "function", "dice::foo")]
    assert {signature.compact for signature in foo.signatures} == {"(cpu_view)", "(cuda_view)"}
    assert set(foo.variants) == {"cpu", "cuda"}
    assert stable_entity_id("cpp", "method", "visible::yes") in merged.entities
    assert stable_entity_id("cpp", "method", "visible::no") not in merged.entities

    macro = merged.entities[stable_entity_id("cpp", "macro", "DICE_BACKEND")]
    assert set(macro.variants) == {"cpu", "cuda"}
    assert set(macro.properties) == {'"cpu"', '"cuda"'}
    assert macro.source is not None and macro.source.path == "dice.hpp"


def test_python_backend_uses_same_graph_model(tmp_path: Path) -> None:
    package = tmp_path / "src" / "dice"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('"""Dice package."""\nfrom .core import Solver\n__all__ = ["Solver"]\n', encoding="utf-8")
    (package / "core.py").write_text(
        '''from typing import Protocol, overload

class Reader(Protocol):
    def read(self, path: str, /, *, binary: bool = False) -> bytes: ...

class Solver:
    def __init__(self, value: int):
        self.value = value

    @overload
    def solve(self, value: int) -> int: ...

    @overload
    def solve(self, value: float) -> float: ...
''',
        encoding="utf-8",
    )

    graph = build_python_graph(
        project_root=tmp_path,
        package_root=package,
        package="dice",
        version="main",
    )
    assert graph.entities[stable_entity_id("python", "package", "dice")].documentation == "Dice package."
    reader = graph.entities[stable_entity_id("python", "protocol", "dice.core.Reader")]
    assert reader.kind == "protocol"
    constructor = graph.entities[stable_entity_id("python", "constructor", "dice.core.Solver.__init__")]
    assert constructor.signatures[0].parameters[1].type == "int"
    solve = graph.entities[stable_entity_id("python", "method", "dice.core.Solver.solve")]
    assert {signature.compact for signature in solve.signatures} == {"(self, int)", "(self, float)"}


def test_rustdoc_backend_normalizes_function_signature(tmp_path: Path) -> None:
    rustdoc = tmp_path / "rustdoc.json"
    rustdoc.write_text(
        json.dumps(
            {
                "index": {
                    "0": {
                        "name": "parse",
                        "visibility": "public",
                        "docs": "Parse a value.",
                        "inner": {
                            "function": {
                                "sig": {
                                    "inputs": [["value", {"borrowed_ref": {"lifetime": None, "is_mutable": False, "type": {"primitive": "str"}}}]],
                                    "output": {"resolved_path": {"name": "Result", "args": {"angle_bracketed": {"args": [{"type": {"primitive": "u64"}}]}}}},
                                },
                                "header": {"is_const": False, "is_async": False, "is_unsafe": False, "abi": "Rust"},
                            }
                        },
                    }
                },
                "paths": {"0": {"path": ["dice", "parse"]}},
            }
        ),
        encoding="utf-8",
    )
    graph = build_rust_graph(rustdoc_json=rustdoc, project="dice", project_root=tmp_path)
    entity = graph.entities[stable_entity_id("rust", "function", "dice::parse")]
    assert entity.signatures[0].compact == "(&str)"
    assert entity.signatures[0].returns == "Result<u64>"


def test_cpp_backend_uses_declared_variant_labels_and_predefinitions() -> None:
    catalog = {
        "variants": [
            {"name": "cpu", "features": ["toolchain-cpp"], "predefined": []},
            {"name": "cuda", "features": ["toolchain-cpp", "toolchain-cuda"], "predefined": ["__CUDACC__=1"]},
        ]
    }
    assert _configuration_name({"variant": "cpu", "variable_features": {}}, 0) == "cpu"
    assert _configuration_name({"variant": "cuda", "variable_features": {}}, 1) == "cuda"
    assert _variant_predefines(catalog, "cuda") == ["__CUDACC__=1"]


def test_renderer_generates_standalone_code_oriented_html_site(tmp_path: Path) -> None:
    graph = ApiGraph(project="dice", version="main", language="cpp")
    namespace = ApiEntity(
        id=stable_entity_id("cpp", "namespace", "dice"),
        language="cpp",
        kind="namespace",
        name="dice",
        qualified_name="dice",
        documentation="Dice public API.",
    )
    function = ApiEntity(
        id=stable_entity_id("cpp", "function", "dice::foo"),
        language="cpp",
        kind="function",
        name="foo",
        qualified_name="dice::foo",
        parent=namespace.id,
        signatures=[
            ApiSignature(parameters=(ApiParameter("value", "int"),), returns="void"),
            ApiSignature(parameters=(ApiParameter("value", "float"),), returns="void"),
        ],
        documentation=(
            "Do work. See [testing guide](projectdocs:reference/testing/#fixtures) and "
            "@projectdocs{blog/}.\n\nBESA-API-RELATES-TO: bar"
        ),
        variants=["cpu"],
    )
    nested_namespace = ApiEntity(
        id=stable_entity_id("cpp", "namespace", "dice::meta"),
        language="cpp",
        kind="namespace",
        name="meta",
        qualified_name="dice::meta",
        parent=namespace.id,
    )
    nested_function = ApiEntity(
        id=stable_entity_id("cpp", "function", "dice::meta::nested"),
        language="cpp",
        kind="function",
        name="nested",
        qualified_name="dice::meta::nested",
        parent=nested_namespace.id,
        signatures=[ApiSignature(returns="void")],
    )
    related = ApiEntity(
        id=stable_entity_id("cpp", "class", "dice::bar"),
        language="cpp",
        kind="class",
        name="bar",
        qualified_name="dice::bar",
        parent=namespace.id,
    )
    method = ApiEntity(
        id=stable_entity_id("cpp", "method", "dice::bar::run"),
        language="cpp",
        kind="method",
        name="run",
        qualified_name="dice::bar::run",
        parent=related.id,
        signatures=[ApiSignature(parameters=(ApiParameter("value", "int"),), returns="void")],
    )
    package_info = ApiEntity(
        id=stable_entity_id("cpp", "struct", "dice::package_info"),
        language="cpp",
        kind="struct",
        name="package_info",
        qualified_name="dice::package_info",
        parent=namespace.id,
    )
    package = ApiEntity(
        id=stable_entity_id("cpp", "function", "dice::package"),
        language="cpp",
        kind="function",
        name="package",
        qualified_name="dice::package",
        parent=namespace.id,
        signatures=[ApiSignature(returns="package_info")],
    )
    macro = ApiEntity(
        id=stable_entity_id("cpp", "macro", "DICE_TEST"),
        language="cpp",
        kind="macro",
        name="DICE_TEST",
        qualified_name="DICE_TEST",
    )
    graph.add(namespace)
    graph.add(nested_namespace)
    graph.add(nested_function)
    graph.add(function)
    graph.add(related)
    graph.add(method)
    graph.add(package_info)
    graph.add(package)
    graph.add(macro)
    graph.sources["dice/version.hpp"] = "#pragma once\nnamespace dice { namespace meta {} }\n"
    graph.variants["cpu"] = {"profile": "cpu", "features": ["toolchain-cpp"], "predefined": []}
    graph.metadata = {
        "catalog": {
            "active_features": ["toolchain-cpp"],
            "project_model": {"features": {"toolchain-cpp": {}}},
            "registrations": [
                {"name": "core", "kind": "source-directory", "path": "src/core", "api": "public"}
            ],
        },
        "variant_manifests": {
            "cpu": {
                "registrations": [
                    {"name": "core", "kind": "source-directory", "path": "src/core", "api": "public", "selected": True}
                ]
            }
        },
    }
    graph.rebuild_children()

    site = tmp_path / "site"
    template = tmp_path / "api-docs"
    template.mkdir()
    (template / "index.md").write_text(
        "# API Documentation Home\n\n"
        "Reference for `{{ project }}` {{ version }}. See the "
        "[project blog](projectdocs:blog/).\n",
        encoding="utf-8",
    )
    render_html_site(
        graph,
        output_directory=site,
        project_docs_url="../../../../../",
        copyright_text="Copyright © dice developers",
        template_directory=template,
    )

    def html_page(document: Path) -> Path:
        if document.name == "index.md":
            return site / document.parent / "index.html"
        return site / document.with_suffix("") / "index.html"

    page = html_page(entity_document(function)).read_text(encoding="utf-8")
    assert '<article class="api-signature-card"' in page
    assert "foo(int)" in page
    assert "API variants" in page
    assert "About API variants and features" in page
    assert "<strong>Related:</strong>" in page
    assert "projectdocs:" not in page
    assert "reference/testing/#fixtures" in page
    assert ">blog</a>" in page
    assert 'class="language-cpp"' in page
    assert (site / "_symbols" / "dice" / "foo" / "index.html").is_file()
    class_page = html_page(entity_document(related)).read_text(encoding="utf-8")
    assert '<code class="language-cpp">' in class_page
    assert "Public Functions" in class_page
    assert 'id="member-method-run"' in class_page
    assert not html_page(entity_document(method)).is_file()
    method_alias = (site / "_symbols" / "dice" / "bar" / "run" / "index.html").read_text(encoding="utf-8")
    assert "#member-method-run" in method_alias
    package_page = html_page(entity_document(package)).read_text(encoding="utf-8")
    assert 'class="besa-api-signature-type"' in package_page
    assert "struct-package_info/" in package_page
    namespace_page = html_page(entity_document(namespace)).read_text(encoding="utf-8")
    assert "Namespace dice" in namespace_page
    assert '<section id="members"' in namespace_page
    assert "Public Functions" not in namespace_page
    assert "Defined in" not in namespace_page
    assert '>foo()</a>' in namespace_page
    assert '>nested()</a>' in namespace_page
    assert '>run</a>' not in namespace_page
    nested_namespace_page = html_page(entity_document(nested_namespace)).read_text(encoding="utf-8")
    assert "groups the public API declared in this scope" in nested_namespace_page
    source_page = (site / "_sources" / "dice" / "version.hpp" / "index.html").read_text(encoding="utf-8")
    assert 'class="language-cpp"' in source_page
    assert "style=" in source_page or "besa-syntax-keyword" in source_page
    home_page = (site / "index.html").read_text(encoding="utf-8")
    assert "projectdocs:" not in home_page
    assert 'href="../../../../../blog/"' in home_page
    assert "Reference for <code>dice</code> main." in home_page
    assert "API hierarchy" in home_page
    assert "File Hierarchy" in home_page
    assert "api-legend" in home_page
    assert "DICE_TEST" in home_page
    assert "Directory dice" in home_page
    assert "File version.hpp" in home_page
    assert (site / "macros" / "index.html").is_file()
    variants_page = (site / "api-variants" / "index.html").read_text(encoding="utf-8")
    assert "Registered project inputs" in variants_page
    assert "Variant selection by feature" in variants_page
    assert "CPU" in variants_page
    assert 'class="api-variant-grid"' in variants_page
    assert 'class="api-variant-card"' in variants_page
    assert (site / "assets" / "besa-api.css").is_file()
    assert (site / "assets" / "besa-api.js").is_file()
    assert "api-outline-children" in home_page
    assert ">run</a>" not in home_page
    assert home_page.count(">foo()</a>") == 2
    assert page.count('class="api-signature-card"') == 2
    class_toc = class_page.split('<aside class="api-toc">', 1)[1]
    assert "run(int)" in class_toc
    css = (site / "assets" / "besa-api.css").read_text(encoding="utf-8")
    assert "grid-template-columns: 20.5rem minmax(0, 1fr) 24rem" in css
    assert "width: min(80%, 80rem)" in css
    assert "--api-tree-indent: 2.45rem" in css
    assert '.api-outline-toggle::before { content: "+"' in css
    assert "border: 1px solid var(--api-border)" in css
    assert '"dice::foo"' in (site / "symbols.json").read_text(encoding="utf-8")
