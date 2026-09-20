# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
"""CMake-profile orchestration for the Clang C++ backend."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path

from .clang_backend import extract_cpp_graph
from .model import ApiGraph, merge_graphs


def _run(command: list[str], *, cwd: Path) -> None:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Command failed:\n  "
            + " ".join(command)
            + "\n\n"
            + result.stdout.rstrip()
        )


def _read_manifest(build_directory: Path) -> dict[str, object]:
    path = build_directory / "besa" / "api-manifest.json"
    if not path.is_file():
        raise RuntimeError(f"BESA API manifest was not produced: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Cannot read BESA API manifest {path}: {error}") from error
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise RuntimeError(f"Unsupported BESA API manifest: {path}")
    return value


def _project_metadata(project_root: Path) -> tuple[str, str]:
    with (project_root / "besa.toml").open("rb") as stream:
        value = tomllib.load(stream)
    project = value.get("project", {})
    if not isinstance(project, dict):
        raise RuntimeError("besa.toml does not contain a [project] table")
    name = str(project.get("name", project_root.name))
    version = str(project.get("version", "main"))
    return name, version


def _catalog(
    *, project_root: Path, work_directory: Path, cmake: str
) -> dict[str, object]:
    build = work_directory / "catalog"
    shutil.rmtree(build, ignore_errors=True)
    command = [
        cmake,
        "-S",
        str(project_root),
        "-B",
        str(build),
        "-DBESA_API_DISCOVERY_ONLY=ON",
        "-DBUILD_TESTING=OFF",
        "-DPROJECT_DEVTOOLS=none",
        "-DPROJECT_WARNINGS=none",
        "-DRELEASE_TYPE=release",
    ]
    _run(command, cwd=project_root)
    return _read_manifest(build)


def _feature_overrides(catalog: dict[str, object], desired: set[str]) -> list[str]:
    model = catalog.get("project_model")
    if not isinstance(model, dict):
        return []
    feature_table = model.get("features")
    if not isinstance(feature_table, dict):
        return []

    overrides: list[str] = []
    for name, raw in feature_table.items():
        if not isinstance(name, str) or not isinstance(raw, dict):
            continue
        default = bool(raw.get("default", False))
        enabled = name in desired
        if name == "user-docs":
            enabled = False
        if enabled != default:
            overrides.append(name if enabled else f"~{name}")
    return overrides


def _configuration_name(configuration: dict[str, object], index: int) -> str:
    profile = configuration.get("profile")
    base = str(profile) if profile else "default"
    variables = configuration.get("variable_features")
    if not isinstance(variables, dict) or not variables:
        return base
    labels = []
    for name, value in sorted(variables.items()):
        labels.append(str(name) if bool(value) else f"~{name}")
    return base + "+" + "+".join(labels)


def _profile_predefines(catalog: dict[str, object], profile_name: str | None) -> list[str]:
    profiles = catalog.get("profiles")
    if not isinstance(profiles, list):
        return []
    for raw in profiles:
        if not isinstance(raw, dict) or str(raw.get("name", "")) != str(profile_name or ""):
            continue
        values = raw.get("predefined")
        if isinstance(values, list):
            return [str(value) for value in values if str(value)]
    return []


def _configuration_space(catalog: dict[str, object]) -> list[dict[str, object]]:
    raw = catalog.get("api_configuration_space")
    if isinstance(raw, dict):
        configurations = raw.get("configurations")
        if isinstance(configurations, list):
            values = [item for item in configurations if isinstance(item, dict)]
            if values:
                return values

    profiles = catalog.get("profiles")
    if isinstance(profiles, list) and profiles:
        return [
            {
                "profile": raw_profile.get("name"),
                "enabled_features": raw_profile.get("features", []),
                "variable_features": {},
            }
            for raw_profile in profiles
            if isinstance(raw_profile, dict)
        ]

    active = catalog.get("active_features")
    return [
        {
            "profile": None,
            "enabled_features": active if isinstance(active, list) else [],
            "variable_features": {},
        }
    ]


def _public_roots(
    *, project_root: Path, build_directory: Path, manifest: dict[str, object]
) -> list[Path]:
    roots: list[Path] = []
    registrations = manifest.get("registrations")
    if isinstance(registrations, list):
        for registration in registrations:
            if not isinstance(registration, dict):
                continue
            if not registration.get("selected") or registration.get("api") == "none":
                continue
            relative = registration.get("path")
            base = registration.get("base")
            kind = registration.get("kind")
            if not isinstance(relative, str) or base not in {"source", "binary"}:
                continue
            root = (project_root if base == "source" else build_directory) / relative
            if kind in {"source-directory", "directory"}:
                root = root / "include"
            if root.is_dir():
                roots.append(root.resolve())

    if not roots:
        roots.extend(path.resolve() for path in project_root.glob("src/*/include") if path.is_dir())
        generated = build_directory / "generated"
        if generated.is_dir():
            roots.extend(path.resolve() for path in generated.glob("*/include") if path.is_dir())

    active = manifest.get("active_features")
    active_features = set(str(value) for value in active) if isinstance(active, list) else set()
    for support in project_root.glob("test/base/*/include"):
        if not support.is_dir():
            continue
        required = f"toolchain-{support.parent.name}"
        if active_features and required not in active_features:
            continue
        roots.append(support.resolve())

    return sorted(set(roots))


def _configure_profile(
    *,
    project_root: Path,
    build_directory: Path,
    catalog: dict[str, object],
    configuration: dict[str, object],
    cmake: str,
) -> dict[str, object]:
    shutil.rmtree(build_directory, ignore_errors=True)
    desired_raw = configuration.get("enabled_features")
    desired = set(str(value) for value in desired_raw) if isinstance(desired_raw, list) else set()
    overrides = _feature_overrides(catalog, desired)

    command = [
        cmake,
        "-S",
        str(project_root),
        "-B",
        str(build_directory),
        "-DBUILD_TESTING=OFF",
        "-DPROJECT_DEVTOOLS=none",
        "-DPROJECT_WARNINGS=none",
        "-DRELEASE_TYPE=release",
        "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
    ]
    if overrides:
        command.append("-DPROJECT_FEATURES=" + ";".join(overrides))
    profile = configuration.get("profile")
    if profile:
        command.append(f"-DBESA_API_PROFILE={profile}")
    _run(command, cwd=project_root)

    manifest = _read_manifest(build_directory)
    registrations = manifest.get("registrations")
    if isinstance(registrations, list) and any(
        isinstance(item, dict)
        and item.get("selected")
        and item.get("kind") == "generated-include"
        and item.get("api") != "none"
        for item in registrations
    ):
        _run([cmake, "--build", str(build_directory), "--target", "besa.generated"], cwd=project_root)
    return manifest


def build_cpp_graph(
    *,
    project_root: Path,
    work_directory: Path,
    version: str | None = None,
    cmake: str = "cmake",
    clang: str | None = None,
    only_profiles: set[str] | None = None,
) -> ApiGraph:
    """Configure each allowed CMake API configuration and merge its Clang semantic graph."""

    project_root = project_root.resolve()
    project, model_version = _project_metadata(project_root)
    effective_version = version or model_version
    work_directory = work_directory.resolve()
    work_directory.mkdir(parents=True, exist_ok=True)

    catalog = _catalog(project_root=project_root, work_directory=work_directory, cmake=cmake)
    configurations = _configuration_space(catalog)
    clang_executable = clang or os.environ.get("BESA_CLANG_EXECUTABLE") or "clang++"

    graphs: list[tuple[str, ApiGraph]] = []
    seen_names: dict[str, int] = {}
    for index, configuration in enumerate(configurations):
        profile_value = configuration.get("profile")
        profile = str(profile_value) if profile_value else None
        if only_profiles is not None and (profile or "default") not in only_profiles:
            continue
        name = _configuration_name(configuration, index)
        count = seen_names.get(name, 0)
        seen_names[name] = count + 1
        if count:
            name = f"{name}-{count + 1}"

        profile_build = work_directory / "profiles" / name / "build"
        manifest = _configure_profile(
            project_root=project_root,
            build_directory=profile_build,
            catalog=catalog,
            configuration=configuration,
            cmake=cmake,
        )
        roots = _public_roots(
            project_root=project_root,
            build_directory=profile_build,
            manifest=manifest,
        )
        graph = extract_cpp_graph(
            project=project,
            version=effective_version,
            project_root=project_root,
            build_directory=profile_build,
            public_roots=roots,
            profile_name=name,
            predefines=_profile_predefines(catalog, profile),
            clang_executable=clang_executable,
            work_directory=work_directory / "profiles" / name / "clang",
        )
        enabled = configuration.get("enabled_features")
        graph.variants[name] = {
            "profile": profile or "default",
            "features": list(enabled) if isinstance(enabled, list) else [],
            "predefined": _profile_predefines(catalog, profile),
        }
        graphs.append((name, graph))

    if not graphs:
        requested = ", ".join(sorted(only_profiles or set())) or "configured API profiles"
        raise RuntimeError(f"No C++ API configurations matched {requested}")

    return merge_graphs(
        graphs,
        project=project,
        version=effective_version,
        language="cpp",
    )
