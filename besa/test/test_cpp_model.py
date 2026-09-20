# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from besa.cli import cpp_generate


def _share_directory() -> Path:
    override = os.environ.get("BESA_SHARE_DIR")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[1] / "share" / "besa"


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        pytest.fail(
            f"Command failed with exit code {result.returncode}: {' '.join(command)}\n\n{result.stdout}",
            pytrace=False,
        )
    return result


@pytest.mark.cpp
def test_project_model_derives_only_relevant_feature_combinations_and_invalidates_callbacks(
    tmp_path: Path,
) -> None:
    project = cpp_generate(tmp_path, "example_model")
    model = project / "besa.toml"
    model.write_text(
        model.read_text(encoding="utf-8")
        + """
[features.api-a]
default = false
kind = "project"

[features.api-b]
default = false
kind = "project"

[features.unrelated]
default = false
kind = "showcase"

[[directories]]
name = "conditional-api"
path = "project/kosha25"
api = "public"
when = { all = ["api-a", "api-b"] }

[[constraints]]
name = "api-pair"
features = ["api-a", "api-b"]
callback = "tools/api_pair.py:check"
""",
        encoding="utf-8",
    )

    tools = project / "tools"
    tools.mkdir()
    callback = tools / "api_pair.py"
    callback.write_text(
        """\
def check(context):
    features = context["features"]
    valid = features["api-a"] == features["api-b"]
    return {"success": True, "result": valid, "reason": "features must match" if not valid else ""}
""",
        encoding="utf-8",
    )

    model_tool = _share_directory() / "cpp" / "cmake" / "python" / "model.py"
    output = tmp_path / "model.cmake"
    normalized = tmp_path / "model.json"
    space = tmp_path / "configurations.json"
    cache = tmp_path / "configure_cache"

    command = [
        sys.executable,
        str(model_tool),
        "emit",
        "--file",
        str(model),
        "--output",
        str(output),
        "--normalized",
        str(normalized),
        "--configuration-space",
        str(space),
        "--cache",
        str(cache),
    ]
    _run(command, project)

    configuration_space = json.loads(space.read_text(encoding="utf-8"))
    assert "api-a" in configuration_space["relevant_features"]
    assert "api-b" in configuration_space["relevant_features"]
    assert "unrelated" not in configuration_space["relevant_features"]
    for configuration in configuration_space["configurations"]:
        variables = configuration["variable_features"]
        assert variables["api-a"] == variables["api-b"]
        assert "unrelated" not in variables

    cache_file = cache / "constraints" / "api-pair.json"
    first_cache = json.loads(cache_file.read_text(encoding="utf-8"))
    assert set(first_cache["accepted"]) == {"00", "11"}

    # The callback implementation is itself part of the cache key. Changing only that function must
    # recompute the finite truth table rather than reusing stale feature logic.
    callback.write_text(
        """\
def check(context):
    features = context["features"]
    valid = features["api-a"] and features["api-b"]
    return {"success": True, "result": valid, "reason": "both features are required" if not valid else ""}
""",
        encoding="utf-8",
    )
    _run(command, project)
    second_cache = json.loads(cache_file.read_text(encoding="utf-8"))
    assert second_cache["fingerprint"] != first_cache["fingerprint"]
    assert second_cache["accepted"] == ["11"]


@pytest.mark.cpp
def test_portable_generator_uses_prefix_contract_and_path_content_for_invalidation(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    inputs = project / "inputs"
    inputs.mkdir()
    source = inputs / "value.txt"
    source.write_text("first\n", encoding="utf-8")

    callback = project / "generator.py"
    callback.write_text(
        """\
def generate(context, output):
    value = (context["input"] / "value.txt").read_text(encoding="utf-8")
    (output / "include" / "generated.hpp").write_text(value, encoding="utf-8")
    return {"success": True, "result": None, "reason": ""}
""",
        encoding="utf-8",
    )
    context = project / "context.json"
    context.write_text(
        json.dumps({"input": {"type": "path", "value": "inputs"}}), encoding="utf-8"
    )

    generator_tool = _share_directory() / "cpp" / "cmake" / "python" / "generator.py"
    output = tmp_path / "codegen" / "probe"
    cache = tmp_path / "configure_cache" / "generators" / "probe.json"
    command = [
        sys.executable,
        str(generator_tool),
        "--callback",
        "generator.py:generate",
        "--context",
        str(context),
        "--project-root",
        str(project),
        "--output",
        str(output),
        "--cache",
        str(cache),
    ]

    _run(command, project)
    assert {path.name for path in output.iterdir()} == {"bin", "include", "lib"}
    assert (output / "include" / "generated.hpp").read_text(encoding="utf-8") == "first\n"
    first = json.loads(cache.read_text(encoding="utf-8"))["fingerprint"]

    source.write_text("second\n", encoding="utf-8")
    _run(command, project)
    assert (output / "include" / "generated.hpp").read_text(encoding="utf-8") == "second\n"
    second = json.loads(cache.read_text(encoding="utf-8"))["fingerprint"]
    assert second != first
