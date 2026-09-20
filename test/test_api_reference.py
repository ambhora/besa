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
from api_reference.model import ApiEntity, ApiGraph, ApiParameter, ApiSignature, merge_graphs, stable_entity_id
from api_reference.python_backend import build_python_graph
from api_reference.render import entity_document, render_properdocs_source
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


def test_renderer_generates_code_oriented_properdocs_site(tmp_path: Path) -> None:
    graph = ApiGraph(project="dice", version="main", language="cpp")
    namespace = ApiEntity(
        id=stable_entity_id("cpp", "namespace", "dice"),
        language="cpp",
        kind="namespace",
        name="dice",
        qualified_name="dice",
    )
    function = ApiEntity(
        id=stable_entity_id("cpp", "function", "dice::foo"),
        language="cpp",
        kind="function",
        name="foo",
        qualified_name="dice::foo",
        parent=namespace.id,
        signatures=[ApiSignature(parameters=(ApiParameter("value", "int"),), returns="void")],
        variants=["cpu"],
    )
    graph.add(namespace)
    graph.add(function)
    graph.variants["cpu"] = {"profile": "cpu", "features": ["toolchain-cpp"], "predefined": []}
    graph.rebuild_children()

    template = tmp_path / "template"
    (template / "assets" / "stylesheets").mkdir(parents=True)
    (template / "assets" / "javascripts").mkdir(parents=True)
    (template / "assets" / "stylesheets" / "besa-api.css").write_text("/* css */\n", encoding="utf-8")
    (template / "assets" / "javascripts" / "besa-api.js").write_text("// js\n", encoding="utf-8")

    source = tmp_path / "generated" / "source"
    config = render_properdocs_source(
        graph,
        source_directory=source,
        output_directory=tmp_path / "site",
        template_directory=template,
        project_docs_url="../../../../../",
        copyright_text="Copyright © dice developers",
    )

    page = (source / entity_document(function)).read_text(encoding="utf-8")
    assert '<article class="besa-api-entity-card">' in page
    assert "foo(int)" in page
    assert "API variants" in page
    assert "api-variants/" in page
    assert (source / "_symbols" / "dice" / "foo" / "index.md").is_file()
    config_text = config.read_text(encoding="utf-8")
    assert 'site_name: "dice API documentation"' in config_text
    assert "assets/stylesheets/besa-api.css" in config_text
