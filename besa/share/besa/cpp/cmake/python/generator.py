#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Portable BESA generator runner.

A generator receives ``generate(context: dict, output: pathlib.Path)`` and must
return either a boolean or ``{"success": bool, "result": ..., "reason": str}``.
The output is a conventional prefix containing bin/, include/, lib/, and
optionally mod/. Context values of the form ``{"type": "path", "value": ...}``
are fingerprinted by content, so edits below those paths invalidate the cache.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from typing import Any


class GeneratorError(RuntimeError):
    pass


def _hash_path(hasher: Any, path: Path) -> None:
    if not path.exists():
        hasher.update(b"missing\0")
        hasher.update(str(path).encode())
        return
    if path.is_file():
        hasher.update(b"file\0")
        hasher.update(path.read_bytes())
        return
    hasher.update(b"dir\0")
    for child in sorted(path.rglob("*")):
        relative = child.relative_to(path).as_posix()
        hasher.update(relative.encode())
        hasher.update(b"\0")
        if child.is_file():
            hasher.update(child.read_bytes())


def _fingerprint_value(hasher: Any, value: Any, project_root: Path) -> Any:
    if isinstance(value, dict) and value.get("type") == "path" and set(value) == {"type", "value"}:
        raw = value["value"]
        if not isinstance(raw, str):
            raise GeneratorError("path context values require a string 'value'")
        hasher.update(b"path\0")
        hasher.update(raw.encode())
        hasher.update(b"\0")
        path = Path(raw)
        if not path.is_absolute():
            path = project_root / path
        path = path.resolve()
        _hash_path(hasher, path)
        return path
    if isinstance(value, dict):
        hasher.update(b"dict\0")
        result = {}
        for key, item in sorted(value.items()):
            hasher.update(str(key).encode())
            hasher.update(b"\0")
            result[key] = _fingerprint_value(hasher, item, project_root)
        return result
    if isinstance(value, list):
        hasher.update(b"list\0")
        return [_fingerprint_value(hasher, item, project_root) for item in value]
    hasher.update(b"value\0")
    hasher.update(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())
    hasher.update(b"\0")
    return value


def _load_callback(reference: str, project_root: Path):
    if ":" not in reference:
        raise GeneratorError("generator callback must use path.py:function syntax")
    path_text, function_name = reference.rsplit(":", 1)
    path = Path(path_text)
    if not path.is_absolute():
        path = project_root / path
    path = path.resolve()
    if not path.is_file():
        raise GeneratorError(f"generator callback file does not exist: {path}")
    spec = importlib.util.spec_from_file_location("_besa_generator", path)
    if spec is None or spec.loader is None:
        raise GeneratorError(f"cannot load generator callback: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    callback = getattr(module, function_name, None)
    if not callable(callback):
        raise GeneratorError(f"generator callback is not callable: {reference}")
    return path, callback


def _validate_result(value: Any) -> None:
    if value is None or value is True:
        return
    if value is False:
        raise GeneratorError("generator returned false")
    if not isinstance(value, dict):
        raise GeneratorError("generator must return None, bool, or a result dictionary")
    success = value.get("success")
    if not isinstance(success, bool):
        raise GeneratorError("generator result.success must be boolean")
    if not success:
        reason = value.get("reason", "generator failed")
        raise GeneratorError(str(reason))


def run(args: argparse.Namespace) -> None:
    project_root = args.project_root.resolve()
    callback_path, callback = _load_callback(args.callback, project_root)
    try:
        raw_context = json.loads(args.context.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise GeneratorError(f"cannot read generator context: {error}") from error
    if not isinstance(raw_context, dict):
        raise GeneratorError("generator context must be a JSON object")

    hasher = hashlib.sha256()
    hasher.update(b"besa-generator-v1\0")
    hasher.update(callback_path.read_bytes())
    context = _fingerprint_value(hasher, raw_context, project_root)
    fingerprint = hasher.hexdigest()

    cache_file = args.cache.resolve()
    output = args.output.resolve()
    if cache_file.is_file() and output.is_dir():
        try:
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cache = None
        if isinstance(cache, dict) and cache.get("fingerprint") == fingerprint:
            return

    shutil.rmtree(output, ignore_errors=True)
    for name in ("bin", "include", "lib"):
        (output / name).mkdir(parents=True, exist_ok=True)
    result = callback(context, output)
    _validate_result(result)

    allowed = {"bin", "include", "lib", "mod"}
    unexpected = sorted(path.name for path in output.iterdir() if path.name not in allowed)
    if unexpected:
        raise GeneratorError("generator output root contains unsupported entries: " + ", ".join(unexpected))

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(
        json.dumps({"schema": 1, "fingerprint": fingerprint}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--callback", required=True)
    result.add_argument("--context", type=Path, required=True)
    result.add_argument("--project-root", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--cache", type=Path, required=True)
    return result


def main() -> int:
    try:
        run(parser().parse_args())
    except GeneratorError as error:
        print(f"besa generator: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
