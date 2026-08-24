#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Parse and validate the build-system-neutral BESA project model.

The TOML file is authoritative.  This helper only normalizes it and emits a
CMake realization for the vendored CMake backend.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import re
import sys
import tomllib
from typing import Any


class ModelError(RuntimeError):
    pass


_TOP_KEYS = {
    "schema",
    "project",
    "features",
    "test-modes",
    "api",
    "dependencies",
    "sources",
    "directories",
    "constraints",
}
_PROJECT_KEYS = {"name", "version"}
_FEATURE_KEYS = {"default", "kind"}
_TEST_MODE_KEYS = {"default"}
_API_KEYS = {"profiles"}
_PROFILE_KEYS = {"features", "predefined"}
_DEPENDENCY_KEYS = {"name", "version", "kind", "provider", "components", "visibility", "when"}
_SOURCE_KEYS = {"name", "path", "language", "api", "when"}
_DIRECTORY_KEYS = {"name", "path", "api", "when"}
_CONSTRAINT_KEYS = {"name", "features", "callback"}
_CONDITION_KEYS = {"all", "any", "not"}
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def _fail(message: str) -> None:
    raise ModelError(message)


def _unknown_keys(where: str, value: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        _fail(f"{where}: unknown keys: {', '.join(unknown)}")


def _table(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{where}: expected a table")
    return value


def _string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"{where}: expected a non-empty string")
    return value


def _bool(value: Any, where: str) -> bool:
    if not isinstance(value, bool):
        _fail(f"{where}: expected true or false")
    return value


def _string_list(value: Any, where: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        _fail(f"{where}: expected an array of non-empty strings")
    if len(value) != len(set(value)):
        _fail(f"{where}: duplicate values are not allowed")
    return list(value)


def _relative_path(value: Any, where: str) -> str:
    text = _string(value, where)
    path = Path(text)
    if path.is_absolute() or ".." in path.parts:
        _fail(f"{where}: path must be source-relative and may not contain '..'")
    return path.as_posix()


def _validate_condition(value: Any, features: set[str], where: str) -> dict[str, Any]:
    table = _table(value, where)
    _unknown_keys(where, table, _CONDITION_KEYS)
    if len(table) != 1:
        _fail(f"{where}: exactly one of all, any, or not is required")
    kind, operand = next(iter(table.items()))
    if kind in {"all", "any"}:
        if not isinstance(operand, list) or not operand:
            _fail(f"{where}.{kind}: expected a non-empty array")
        normalized: list[Any] = []
        for index, item in enumerate(operand):
            item_where = f"{where}.{kind}[{index}]"
            if isinstance(item, str):
                if item not in features:
                    _fail(f"{item_where}: unknown feature '{item}'")
                normalized.append(item)
            else:
                normalized.append(_validate_condition(item, features, item_where))
        return {kind: normalized}
    if isinstance(operand, str):
        if operand not in features:
            _fail(f"{where}.not: unknown feature '{operand}'")
        return {"not": operand}
    return {"not": _validate_condition(operand, features, f"{where}.not")}


def _condition_features(condition: dict[str, Any] | None) -> set[str]:
    if not condition:
        return set()
    kind, operand = next(iter(condition.items()))
    if kind == "not":
        return {operand} if isinstance(operand, str) else _condition_features(operand)
    result: set[str] = set()
    for item in operand:
        if isinstance(item, str):
            result.add(item)
        else:
            result.update(_condition_features(item))
    return result


def _condition_matches(condition: dict[str, Any] | None, enabled: set[str]) -> bool:
    if not condition:
        return True
    kind, operand = next(iter(condition.items()))
    if kind == "all":
        return all(
            item in enabled if isinstance(item, str) else _condition_matches(item, enabled)
            for item in operand
        )
    if kind == "any":
        return any(
            item in enabled if isinstance(item, str) else _condition_matches(item, enabled)
            for item in operand
        )
    if isinstance(operand, str):
        return operand not in enabled
    return not _condition_matches(operand, enabled)


def load_model(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as stream:
            raw = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as error:
        _fail(f"cannot read {path}: {error}")

    _unknown_keys("besa.toml", raw, _TOP_KEYS)
    if raw.get("schema") != 1:
        _fail("besa.toml: schema must be 1")

    project = _table(raw.get("project"), "project")
    _unknown_keys("project", project, _PROJECT_KEYS)
    project_name = _string(project.get("name"), "project.name")
    project_version = _string(project.get("version"), "project.version")

    raw_features = _table(raw.get("features", {}), "features")
    features: dict[str, dict[str, Any]] = {}
    for name, value in raw_features.items():
        if not _NAME_RE.fullmatch(name):
            _fail(f"features.{name}: invalid feature name")
        table = _table(value, f"features.{name}")
        _unknown_keys(f"features.{name}", table, _FEATURE_KEYS)
        features[name] = {
            "default": _bool(table.get("default", False), f"features.{name}.default"),
            "kind": _string(table.get("kind", "general"), f"features.{name}.kind"),
        }
    feature_names = set(features)

    raw_modes = _table(raw.get("test-modes", {}), "test-modes")
    test_modes: dict[str, dict[str, Any]] = {}
    for name, value in raw_modes.items():
        table = _table(value, f"test-modes.{name}")
        _unknown_keys(f"test-modes.{name}", table, _TEST_MODE_KEYS)
        test_modes[name] = {"default": _bool(table.get("default", False), f"test-modes.{name}.default")}

    api = _table(raw.get("api", {}), "api")
    _unknown_keys("api", api, _API_KEYS)
    raw_profiles = _table(api.get("profiles", {}), "api.profiles")
    profiles: dict[str, dict[str, Any]] = {}
    for name, value in raw_profiles.items():
        table = _table(value, f"api.profiles.{name}")
        _unknown_keys(f"api.profiles.{name}", table, _PROFILE_KEYS)
        profile_features = _string_list(table.get("features", []), f"api.profiles.{name}.features")
        for feature in profile_features:
            if feature not in feature_names:
                _fail(f"api.profiles.{name}.features: unknown feature '{feature}'")
        profiles[name] = {
            "features": profile_features,
            "predefined": _string_list(table.get("predefined", []), f"api.profiles.{name}.predefined"),
        }

    def normalize_records(key: str, allowed: set[str]) -> list[dict[str, Any]]:
        values = raw.get(key, [])
        if not isinstance(values, list):
            _fail(f"{key}: expected an array of tables")
        result: list[dict[str, Any]] = []
        for index, item in enumerate(values):
            where = f"{key}[{index}]"
            table = _table(item, where)
            _unknown_keys(where, table, allowed)
            result.append(dict(table))
        return result

    dependencies = normalize_records("dependencies", _DEPENDENCY_KEYS)
    for index, item in enumerate(dependencies):
        where = f"dependencies[{index}]"
        item["name"] = _string(item.get("name"), f"{where}.name")
        item["version"] = str(item.get("version", ""))
        item["kind"] = _string(item.get("kind", "normal"), f"{where}.kind").lower()
        item["provider"] = _string(item.get("provider", "cmake"), f"{where}.provider").lower()
        item["visibility"] = _string(item.get("visibility", "private"), f"{where}.visibility").lower()
        item["components"] = _string_list(item.get("components", []), f"{where}.components")
        if item["kind"] not in {"normal", "build", "dev"}:
            _fail(f"{where}.kind: expected normal, build, or dev")
        if item["provider"] not in {"cmake", "pkgconfig"}:
            _fail(f"{where}.provider: expected cmake or pkgconfig")
        if item["visibility"] not in {"public", "private", "interface"}:
            _fail(f"{where}.visibility: expected public, private, or interface")
        item["when"] = (
            _validate_condition(item["when"], feature_names, f"{where}.when") if "when" in item else None
        )

    sources = normalize_records("sources", _SOURCE_KEYS)
    for index, item in enumerate(sources):
        where = f"sources[{index}]"
        item["name"] = _string(item.get("name"), f"{where}.name")
        item["path"] = _relative_path(item.get("path"), f"{where}.path")
        item["language"] = _string(item.get("language"), f"{where}.language")
        item["api"] = _string(item.get("api", "public"), f"{where}.api").lower()
        if item["api"] not in {"public", "none"}:
            _fail(f"{where}.api: expected public or none")
        item["when"] = (
            _validate_condition(item["when"], feature_names, f"{where}.when") if "when" in item else None
        )

    directories = normalize_records("directories", _DIRECTORY_KEYS)
    for index, item in enumerate(directories):
        where = f"directories[{index}]"
        item["name"] = _string(item.get("name"), f"{where}.name")
        item["path"] = _relative_path(item.get("path"), f"{where}.path")
        item["api"] = _string(item.get("api", "none"), f"{where}.api").lower()
        if item["api"] not in {"public", "none"}:
            _fail(f"{where}.api: expected public or none")
        item["when"] = (
            _validate_condition(item["when"], feature_names, f"{where}.when") if "when" in item else None
        )

    constraints = normalize_records("constraints", _CONSTRAINT_KEYS)
    for index, item in enumerate(constraints):
        where = f"constraints[{index}]"
        item["name"] = _string(item.get("name"), f"{where}.name")
        item["features"] = _string_list(item.get("features", []), f"{where}.features")
        if not item["features"]:
            _fail(f"{where}.features: at least one feature is required")
        for feature in item["features"]:
            if feature not in feature_names:
                _fail(f"{where}.features: unknown feature '{feature}'")
        item["callback"] = _string(item.get("callback"), f"{where}.callback")

    return {
        "schema": 1,
        "project": {"name": project_name, "version": project_version},
        "features": features,
        "test-modes": test_modes,
        "api": {"profiles": profiles},
        "dependencies": dependencies,
        "sources": sources,
        "directories": directories,
        "constraints": constraints,
    }


def _callback_source(model_path: Path, reference: str) -> tuple[Path, str]:
    if ":" not in reference:
        _fail(f"callback '{reference}' must use path.py:function syntax")
    path_text, function = reference.rsplit(":", 1)
    path = (model_path.parent / path_text).resolve()
    if not path.is_file():
        _fail(f"callback file does not exist: {path}")
    if not function.isidentifier():
        _fail(f"invalid callback function name '{function}'")
    return path, function


def _normalize_callback_result(value: Any, *, name: str) -> tuple[bool, bool, str]:
    if isinstance(value, bool):
        return True, value, ""
    if not isinstance(value, dict):
        _fail(f"constraint '{name}' callback must return bool or a result dictionary")
    success = value.get("success")
    result = value.get("result")
    reason = value.get("reason", "")
    if not isinstance(success, bool):
        _fail(f"constraint '{name}' result.success must be boolean")
    if not success:
        _fail(f"constraint '{name}' callback failed: {reason or 'no reason supplied'}")
    if not isinstance(result, bool):
        _fail(f"constraint '{name}' result.result must be boolean")
    if not isinstance(reason, str):
        _fail(f"constraint '{name}' result.reason must be a string")
    return success, result, reason


def _constraint_truth_table(model: dict[str, Any], model_path: Path, cache_dir: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    cache_dir.mkdir(parents=True, exist_ok=True)
    for constraint in model["constraints"]:
        callback_path, function_name = _callback_source(model_path, constraint["callback"])
        fingerprint = hashlib.sha256()
        fingerprint.update(b"besa-constraint-v1\0")
        fingerprint.update(json.dumps(constraint, sort_keys=True).encode())
        fingerprint.update(callback_path.read_bytes())
        digest = fingerprint.hexdigest()
        cache_file = cache_dir / f"{constraint['name']}.json"
        if cache_file.is_file():
            try:
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                cached = None
            if isinstance(cached, dict) and cached.get("fingerprint") == digest:
                result[constraint["name"]] = cached
                continue

        spec = importlib.util.spec_from_file_location(f"_besa_constraint_{constraint['name']}", callback_path)
        if spec is None or spec.loader is None:
            _fail(f"cannot load constraint callback {callback_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        callback = getattr(module, function_name, None)
        if not callable(callback):
            _fail(f"constraint callback '{function_name}' is not callable in {callback_path}")

        features = constraint["features"]
        accepted: list[str] = []
        reasons: dict[str, str] = {}
        for values in itertools.product((False, True), repeat=len(features)):
            assignment = dict(zip(features, values, strict=True))
            callback_result = callback({"features": assignment})
            _, valid, reason = _normalize_callback_result(callback_result, name=constraint["name"])
            key = "".join("1" if value else "0" for value in values)
            if valid:
                accepted.append(key)
            elif reason:
                reasons[key] = reason
        cached = {
            "schema": 1,
            "name": constraint["name"],
            "features": features,
            "callback": constraint["callback"],
            "fingerprint": digest,
            "accepted": accepted,
            "reasons": reasons,
        }
        cache_file.write_text(json.dumps(cached, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result[constraint["name"]] = cached
    return result


def _constraints_accept(enabled: set[str], tables: dict[str, dict[str, Any]]) -> bool:
    for table in tables.values():
        key = "".join("1" if feature in enabled else "0" for feature in table["features"])
        if key not in set(table["accepted"]):
            return False
    return True


def _configuration_space(model: dict[str, Any], tables: dict[str, dict[str, Any]]) -> dict[str, Any]:
    public_records = [
        item
        for key in ("sources", "directories")
        for item in model[key]
        if item["api"] == "public"
    ]
    relevant: set[str] = set()
    for item in public_records:
        relevant.update(_condition_features(item["when"]))

    # If one constraint touches an API-relevant feature, every feature used by that constraint is
    # part of the same finite domain. Repeat to a fixed point for overlapping constraints.
    changed = True
    while changed:
        changed = False
        for table in tables.values():
            domain = set(table["features"])
            if relevant.intersection(domain) and not domain.issubset(relevant):
                relevant.update(domain)
                changed = True

    features = model["features"]
    toolchain_features = {name for name, data in features.items() if data["kind"] == "toolchain"}
    profiles = model["api"]["profiles"]
    configurations: list[dict[str, Any]] = []
    for profile_name, profile in profiles.items():
        fixed_true = set(profile["features"])
        variable = sorted(relevant - fixed_true - toolchain_features)
        for values in itertools.product((False, True), repeat=len(variable)):
            enabled = {name for name, data in features.items() if data["default"]}
            enabled.difference_update(toolchain_features)
            enabled.update(fixed_true)
            for name, value in zip(variable, values, strict=True):
                if value:
                    enabled.add(name)
                else:
                    enabled.discard(name)
            if not _constraints_accept(enabled, tables):
                continue
            if public_records and not any(_condition_matches(item["when"], enabled) for item in public_records):
                continue
            configurations.append(
                {
                    "profile": profile_name,
                    "enabled_features": sorted(enabled),
                    "variable_features": {name: value for name, value in zip(variable, values, strict=True)},
                }
            )
    return {
        "schema": 1,
        "relevant_features": sorted(relevant),
        "configurations": configurations,
    }


def _cmake_bracket(value: str) -> str:
    marker = ""
    while f"]{marker}]" in value:
        marker += "="
    return f"[{marker}[{value}]{marker}]"


def _condition_json(condition: dict[str, Any]) -> str:
    return json.dumps(condition, separators=(",", ":"), sort_keys=True)


def _emit_selector(lines: list[str], name: str, condition: dict[str, Any] | None) -> str | None:
    if not condition:
        return None
    function = f"_besa_model_selector_{name}"
    expression = _cmake_bracket(_condition_json(condition))
    lines.extend(
        [
            f"function({function})",
            "  besa_selector_arguments_parse(PREFIX ARG ARGUMENTS ${ARGN})",
            f"  _besa_model_condition_evaluate({expression} \"${{ARG_FEATURES}}\" _selected)",
            "  set(\"${ARG_OUTPUT_VARIABLE}\" \"${_selected}\" PARENT_SCOPE)",
            "  set(\"${ARG_ERROR_VARIABLE}\" \"\" PARENT_SCOPE)",
            "endfunction()",
            "",
        ]
    )
    return function


def emit_cmake(model: dict[str, Any], tables: dict[str, dict[str, Any]]) -> str:
    lines = ["# Generated from besa.toml. Do not edit.", ""]
    feature_names = list(model["features"])
    lines += ["besa_features_add(", "  FEATURES", *(f"  {_cmake_bracket(x)}" for x in feature_names), ")", ""]
    defaults = [name for name, data in model["features"].items() if data["default"]]
    if defaults:
        lines += ["besa_features_default(", "  FEATURES", *(f"  {_cmake_bracket(x)}" for x in defaults), ")", ""]
    for name, data in model["features"].items():
        lines.append(f"set_property(GLOBAL PROPERTY BESA_FEATURE_KIND_{name} {_cmake_bracket(data['kind'])})")
    lines.append("")

    for name, profile in model["api"]["profiles"].items():
        lines += ["besa_api_profile_add(", f"  NAME {_cmake_bracket(name)}", "  FEATURES"]
        lines += [f"  {_cmake_bracket(x)}" for x in profile["features"]]
        if profile["predefined"]:
            lines.append("  PREDEFINED")
            lines += [f"  {_cmake_bracket(x)}" for x in profile["predefined"]]
        lines += [")", ""]

    modes = list(model["test-modes"])
    if modes:
        lines += ["besa_test_modes_add(", "  MODES", *(f"  {_cmake_bracket(x)}" for x in modes), ")", ""]
        mode_defaults = [name for name, data in model["test-modes"].items() if data["default"]]
        if mode_defaults:
            lines += ["besa_test_modes_default(", "  MODES", *(f"  {_cmake_bracket(x)}" for x in mode_defaults), ")", ""]

    for index, constraint in enumerate(model["constraints"]):
        table = tables[constraint["name"]]
        function = f"_besa_model_constraint_{index}"
        features = ";".join(table["features"])
        accepted = ";".join(table["accepted"])
        lines += [
            f"function({function})",
            "  besa_feature_constraint_arguments_parse(PREFIX ARG ARGUMENTS ${ARGN})",
            f"  _besa_model_constraint_evaluate({_cmake_bracket(features)} {_cmake_bracket(accepted)} \"${{ARG_FEATURES}}\" _valid)",
            "  set(\"${ARG_OUTPUT_VARIABLE}\" \"${_valid}\" PARENT_SCOPE)",
            "  if(_valid)",
            "    set(\"${ARG_ERROR_VARIABLE}\" \"\" PARENT_SCOPE)",
            "  else()",
            f"    set(\"${{ARG_ERROR_VARIABLE}}\" {_cmake_bracket('feature constraint ' + constraint['name'] + ' rejected the configuration')} PARENT_SCOPE)",
            "  endif()",
            "endfunction()",
            f"besa_register_feature_constraint(FUNCTION {function})",
            "",
        ]

    lines += ["besa_configure_complete()", ""]

    selector_count = 0
    for group in ("dependencies", "sources", "directories"):
        for item in model[group]:
            selector = _emit_selector(lines, str(selector_count), item["when"])
            selector_count += 1
            when = f" WHEN FUNCTION {selector}" if selector else ""
            if group == "dependencies":
                args = [
                    "besa_dependency_add(",
                    f"  NAME {_cmake_bracket(item['name'])}",
                    f"  KIND {item['kind'].upper()}",
                    f"  PROVIDER {item['provider'].upper()}",
                    f"  VISIBILITY {item['visibility'].upper()}",
                ]
                if item["version"]:
                    args.append(f"  VERSION {_cmake_bracket(item['version'])}")
                if item["components"]:
                    args.append("  COMPONENTS")
                    args.extend(f"  {_cmake_bracket(x)}" for x in item["components"])
                if selector:
                    args += ["  WHEN", "  FUNCTION", f"  {selector}"]
                args += [")", ""]
                lines += args
            elif group == "sources":
                lines += [
                    "besa_add_source_directory(",
                    f"  NAME {_cmake_bracket(item['name'])}",
                    f"  PATH {_cmake_bracket(item['path'])}",
                    f"  LANGUAGE {_cmake_bracket(item['language'])}",
                    f"  API {item['api'].upper()}",
                ]
                if selector:
                    lines += ["  WHEN", "  FUNCTION", f"  {selector}"]
                lines += [")", ""]
            else:
                lines += [
                    "besa_add_directory(",
                    f"  NAME {_cmake_bracket(item['name'])}",
                    f"  PATH {_cmake_bracket(item['path'])}",
                    f"  API {item['api'].upper()}",
                ]
                if selector:
                    lines += ["  WHEN", "  FUNCTION", f"  {selector}"]
                lines += [")", ""]
    return "\n".join(lines)


def command_bootstrap(args: argparse.Namespace) -> None:
    model = load_model(args.file)
    text = "\n".join(
        [
            "# Generated from besa.toml. Do not edit.",
            f"set(BESA_MODEL_PROJECT_NAME {_cmake_bracket(model['project']['name'])})",
            f"set(BESA_MODEL_PROJECT_VERSION {_cmake_bracket(model['project']['version'])})",
            "",
        ]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")


def command_emit(args: argparse.Namespace) -> None:
    model = load_model(args.file)
    tables = _constraint_truth_table(model, args.file, args.cache / "constraints")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(emit_cmake(model, tables), encoding="utf-8")
    args.normalized.parent.mkdir(parents=True, exist_ok=True)
    args.normalized.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    space = _configuration_space(model, tables)
    args.configuration_space.parent.mkdir(parents=True, exist_ok=True)
    args.configuration_space.write_text(json.dumps(space, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    subcommands = result.add_subparsers(dest="command", required=True)
    bootstrap = subcommands.add_parser("bootstrap")
    bootstrap.add_argument("--file", type=Path, required=True)
    bootstrap.add_argument("--output", type=Path, required=True)
    bootstrap.set_defaults(handler=command_bootstrap)
    emit = subcommands.add_parser("emit")
    emit.add_argument("--file", type=Path, required=True)
    emit.add_argument("--output", type=Path, required=True)
    emit.add_argument("--normalized", type=Path, required=True)
    emit.add_argument("--configuration-space", type=Path, required=True)
    emit.add_argument("--cache", type=Path, required=True)
    emit.set_defaults(handler=command_emit)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        args.handler(args)
    except ModelError as error:
        print(f"besa model: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
