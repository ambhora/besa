# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
"""Clang semantic-AST backend for C and C++ API extraction.

The backend intentionally treats Clang as the semantic authority.  It invokes the compiler frontend
with ``-ast-dump=json`` only as a transport format; the rest of BESA consumes the normalized
:class:`ApiGraph`, so this adapter can later be replaced by LibTooling without touching rendering,
versioning, or availability handling.
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from .model import ApiEntity, ApiGraph, ApiParameter, ApiSignature, SourceLocation, relative_source_path, stable_entity_id

_RECORD_KINDS = {
    "CXXRecordDecl": "class",
    "RecordDecl": "struct",
    "ClassTemplateDecl": "class",
    "ClassTemplatePartialSpecializationDecl": "class",
    "ClassTemplateSpecializationDecl": "class",
}
_CALLABLE_KINDS = {
    "FunctionDecl": "function",
    "CXXMethodDecl": "method",
    "CXXConstructorDecl": "constructor",
    "CXXDestructorDecl": "method",
    "ConversionFunctionDecl": "method",
}
_ALIAS_KINDS = {"TypedefDecl": "type_alias", "TypeAliasDecl": "type_alias"}
_VARIABLE_KINDS = {"VarDecl": "variable", "FieldDecl": "attribute"}
_SKIP_NAMES = {"__va_list_tag", "__NSConstantString_tag"}


def _node_file(
    node: dict[str, object],
    inherited: Path | None,
    file_state: list[Path | None],
) -> Path | None:
    """Resolve Clang's state-compressed JSON source location to an explicit file path."""

    loc = node.get("loc")
    if isinstance(loc, dict):
        file_value = loc.get("file")
        if isinstance(file_value, str) and file_value:
            value = Path(file_value)
            file_state[0] = value
            return value
    if inherited is not None:
        return inherited
    return file_state[0]


@lru_cache(maxsize=256)
def _source_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        return b""


def _line_column_from_offset(path: Path, offset: int) -> tuple[int | None, int | None]:
    content = _source_bytes(path)
    if not content or offset < 0 or offset > len(content):
        return None, None
    before = content[:offset]
    line = before.count(b"\n") + 1
    last_newline = before.rfind(b"\n")
    column = offset + 1 if last_newline < 0 else offset - last_newline
    return line, column


def _inside(path: Path | None, roots: Iterable[Path]) -> bool:
    if path is None:
        return False
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    for root in roots:
        try:
            resolved.relative_to(root.resolve())
            return True
        except (OSError, ValueError):
            continue
    return False


def _logical_public_path(path: Path, public_roots: tuple[Path, ...], project_root: Path) -> str:
    for root in public_roots:
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except (OSError, ValueError):
            continue
    return relative_source_path(path, project_root)


def _comment_text(node: dict[str, object]) -> str:
    paragraphs: list[str] = []

    def flatten(current: dict[str, object]) -> str:
        kind = str(current.get("kind", ""))
        text = current.get("text")
        if isinstance(text, str):
            return text.strip()
        children = current.get("inner")
        parts: list[str] = []
        if isinstance(children, list):
            for child in children:
                if isinstance(child, dict):
                    value = flatten(child)
                    if value:
                        parts.append(value)
        if kind == "ParamCommandComment":
            parameter = current.get("param") or current.get("paramName")
            body = " ".join(parts).strip()
            if parameter:
                return f"**{parameter}** — {body}" if body else f"**{parameter}**"
        if kind == "BlockCommandComment":
            command = current.get("name")
            body = " ".join(parts).strip()
            if command in {"return", "returns"} and body:
                return f"Returns: {body}"
        return " ".join(parts).strip()

    children = node.get("inner")
    if isinstance(children, list):
        for child in children:
            if not isinstance(child, dict):
                continue
            value = flatten(child)
            if value:
                paragraphs.append(value)
    return "\n\n".join(paragraphs)


def _attached_comment(node: dict[str, object]) -> str:
    children = node.get("inner")
    if not isinstance(children, list):
        return ""
    for child in children:
        if isinstance(child, dict) and child.get("kind") == "FullComment":
            return _comment_text(child)
    return ""


def _location(
    node: dict[str, object],
    path: Path | None,
    project_root: Path,
    public_roots: tuple[Path, ...],
) -> SourceLocation | None:
    if path is None:
        return None
    loc = node.get("loc")
    line = None
    column = None
    if isinstance(loc, dict):
        if isinstance(loc.get("line"), int):
            line = int(loc["line"])
        if isinstance(loc.get("col"), int):
            column = int(loc["col"])
        if (line is None or column is None) and isinstance(loc.get("offset"), int):
            inferred_line, inferred_column = _line_column_from_offset(path, int(loc["offset"]))
            line = line or inferred_line
            column = column or inferred_column
    # Public API locations use the installed/header namespace where possible. Generated headers
    # therefore do not leak profile-specific build-directory paths into the published reference.
    return SourceLocation(_logical_public_path(path, public_roots, project_root), line, column)


def _qual_type(node: dict[str, object]) -> str:
    value = node.get("type")
    if isinstance(value, dict):
        spelling = value.get("qualType")
        if isinstance(spelling, str):
            return spelling
    return ""


def _parameters(node: dict[str, object]) -> tuple[ApiParameter, ...]:
    parameters: list[ApiParameter] = []
    children = node.get("inner")
    if not isinstance(children, list):
        return ()
    for child in children:
        if not isinstance(child, dict) or child.get("kind") != "ParmVarDecl":
            continue
        parameters.append(
            ApiParameter(
                name=str(child.get("name", "")),
                type=_qual_type(child),
            )
        )
    return tuple(parameters)


def _return_type(node: dict[str, object]) -> str:
    kind = str(node.get("kind", ""))
    if kind in {"CXXConstructorDecl", "CXXDestructorDecl"}:
        return ""
    spelling = _qual_type(node)
    if not spelling:
        return ""
    marker = spelling.find(" (")
    if marker >= 0:
        return spelling[:marker].strip()
    return ""


def _qualifiers(node: dict[str, object]) -> tuple[str, ...]:
    values: list[str] = []
    for field, label in (
        ("inline", "inline"),
        ("constexpr", "constexpr"),
        ("consteval", "consteval"),
        ("virtual", "virtual"),
        ("pure", "pure virtual"),
    ):
        if node.get(field) is True:
            values.append(label)
    storage = node.get("storageClass")
    if isinstance(storage, str) and storage:
        values.append(storage)
    spelling = _qual_type(node)
    suffix = spelling.rsplit(")", 1)[1] if ")" in spelling else ""
    for token in ("const", "volatile", "noexcept"):
        if re.search(rf"\b{token}\b", suffix) and token not in values:
            values.append(token)
    if "&&" in suffix:
        values.append("&&")
    elif "&" in suffix:
        values.append("&")
    return tuple(values)


def _signature(node: dict[str, object]) -> ApiSignature:
    parameters = _parameters(node)
    qualifiers = _qualifiers(node)
    return ApiSignature(parameters=parameters, returns=_return_type(node), qualifiers=qualifiers)


def _record_kind(node: dict[str, object]) -> str:
    tag = node.get("tagUsed")
    if isinstance(tag, str) and tag in {"class", "struct", "union"}:
        return tag
    return _RECORD_KINDS.get(str(node.get("kind", "")), "class")


def _entity_properties(node: dict[str, object]) -> list[str]:
    properties = list(_qualifiers(node))
    access = node.get("access")
    if isinstance(access, str) and access not in {"", "public"}:
        properties.append(access)
    if node.get("isAggregate") is True:
        properties.append("aggregate")
    return list(dict.fromkeys(properties))


def _base_names(node: dict[str, object]) -> list[str]:
    values: list[str] = []
    bases = node.get("bases")
    if isinstance(bases, list):
        for base in bases:
            if not isinstance(base, dict):
                continue
            spelling = _qual_type(base)
            if spelling and spelling not in values:
                values.append(spelling)
    return values


def _walk_ast(
    node: dict[str, object],
    *,
    graph: ApiGraph,
    project_root: Path,
    public_roots: tuple[Path, ...],
    inherited_file: Path | None = None,
    parent_entity: ApiEntity | None = None,
    scopes: tuple[str, ...] = (),
    template_context: bool = False,
    access: str = "public",
    file_state: list[Path | None] | None = None,
) -> None:
    if file_state is None:
        file_state = [inherited_file]
    kind = str(node.get("kind", ""))
    path = _node_file(node, inherited_file, file_state)
    name = str(node.get("name", ""))
    in_public_file = _inside(path, public_roots)

    if node.get("isImplicit") is True:
        return
    if name in _SKIP_NAMES:
        return

    # Clang represents C++ access changes as ordered AccessSpecDecl siblings rather than copying the
    # access level onto every member. The parent traversal supplies the effective access here.
    if access != "public" and kind in {
        *_RECORD_KINDS,
        *_CALLABLE_KINDS,
        *_ALIAS_KINDS,
        *_VARIABLE_KINDS,
        "EnumDecl",
        "ConceptDecl",
        "FunctionTemplateDecl",
    }:
        return

    entity: ApiEntity | None = None
    next_scopes = scopes
    next_parent = parent_entity
    next_template = template_context or kind in {"FunctionTemplateDecl", "ClassTemplateDecl"}

    if kind == "NamespaceDecl" and name and in_public_file:
        qualified = "::".join((*scopes, name))
        entity = ApiEntity(
            id=stable_entity_id("cpp", "namespace", qualified),
            language="cpp",
            kind="namespace",
            name=name,
            qualified_name=qualified,
            parent=parent_entity.id if parent_entity else None,
            documentation=_attached_comment(node),
            source=_location(node, path, project_root, public_roots),
        )
        graph.add(entity)
        entity = graph.entities[entity.id]
        next_scopes = (*scopes, name)
        next_parent = entity

    elif kind in _RECORD_KINDS and name and in_public_file:
        # ClassTemplateDecl wraps the actual CXXRecordDecl.  Let the record child own the semantic
        # entity, but propagate template context so it receives a template property.
        if kind == "ClassTemplateDecl":
            pass
        else:
            qualified = "::".join((*scopes, name))
            record_kind = _record_kind(node)
            entity = ApiEntity(
                id=stable_entity_id("cpp", record_kind, qualified),
                language="cpp",
                kind=record_kind,
                name=name,
                qualified_name=qualified,
                parent=parent_entity.id if parent_entity else None,
                documentation=_attached_comment(node),
                source=_location(node, path, project_root, public_roots),
                properties=_entity_properties(node) + (["template"] if template_context else []),
                bases=_base_names(node),
            )
            graph.add(entity)
            entity = graph.entities[entity.id]
            next_scopes = (*scopes, name)
            next_parent = entity

    elif kind in _CALLABLE_KINDS and name and in_public_file:
        qualified = "::".join((*scopes, name))
        callable_kind = _CALLABLE_KINDS[kind]
        entity_id = stable_entity_id("cpp", callable_kind, qualified)
        entity = ApiEntity(
            id=entity_id,
            language="cpp",
            kind=callable_kind,
            name=name,
            qualified_name=qualified,
            parent=parent_entity.id if parent_entity else None,
            signatures=[_signature(node)],
            documentation=_attached_comment(node),
            source=_location(node, path, project_root, public_roots),
            properties=_entity_properties(node) + (["template"] if template_context else []),
        )
        graph.add(entity)
        next_parent = graph.entities[entity_id]

    elif kind == "EnumDecl" and name and in_public_file:
        qualified = "::".join((*scopes, name))
        entity = ApiEntity(
            id=stable_entity_id("cpp", "enum", qualified),
            language="cpp",
            kind="enum",
            name=name,
            qualified_name=qualified,
            parent=parent_entity.id if parent_entity else None,
            documentation=_attached_comment(node),
            source=_location(node, path, project_root, public_roots),
            properties=["scoped"] if node.get("scopedEnumTag") else [],
        )
        graph.add(entity)
        entity = graph.entities[entity.id]
        next_scopes = (*scopes, name)
        next_parent = entity

    elif kind == "EnumConstantDecl" and name and in_public_file:
        qualified = "::".join((*scopes, name))
        entity = ApiEntity(
            id=stable_entity_id("cpp", "constant", qualified),
            language="cpp",
            kind="constant",
            name=name,
            qualified_name=qualified,
            parent=parent_entity.id if parent_entity else None,
            documentation=_attached_comment(node),
            source=_location(node, path, project_root, public_roots),
        )
        graph.add(entity)

    elif kind in _ALIAS_KINDS and name and in_public_file:
        qualified = "::".join((*scopes, name))
        target = _qual_type(node)
        entity = ApiEntity(
            id=stable_entity_id("cpp", "type_alias", qualified),
            language="cpp",
            kind="type_alias",
            name=name,
            qualified_name=qualified,
            parent=parent_entity.id if parent_entity else None,
            documentation=_attached_comment(node),
            source=_location(node, path, project_root, public_roots),
            properties=[f"= {target}"] if target else [],
        )
        graph.add(entity)

    elif kind in _VARIABLE_KINDS and name and in_public_file:
        qualified = "::".join((*scopes, name))
        variable_kind = _VARIABLE_KINDS[kind]
        entity = ApiEntity(
            id=stable_entity_id("cpp", variable_kind, qualified),
            language="cpp",
            kind=variable_kind,
            name=name,
            qualified_name=qualified,
            parent=parent_entity.id if parent_entity else None,
            documentation=_attached_comment(node),
            source=_location(node, path, project_root, public_roots),
            properties=[_qual_type(node)] if _qual_type(node) else [],
        )
        graph.add(entity)

    elif kind == "ConceptDecl" and name and in_public_file:
        qualified = "::".join((*scopes, name))
        entity = ApiEntity(
            id=stable_entity_id("cpp", "concept", qualified),
            language="cpp",
            kind="concept",
            name=name,
            qualified_name=qualified,
            parent=parent_entity.id if parent_entity else None,
            documentation=_attached_comment(node),
            source=_location(node, path, project_root, public_roots),
        )
        graph.add(entity)

    # Callable bodies, variable initializers, aliases, and concepts can contain declarations that are
    # implementation details. Their semantic metadata has already been harvested above; only
    # namespace/record/enum/template containers should contribute nested public API entities.
    if kind in {*_CALLABLE_KINDS, *_ALIAS_KINDS, *_VARIABLE_KINDS, "ConceptDecl", "EnumConstantDecl"}:
        return

    children = node.get("inner")
    if not isinstance(children, list):
        return

    # Comments and parameter declarations are metadata, not API entities. For records, preserve the
    # source-order access state because Clang emits AccessSpecDecl markers as siblings.
    member_access = access
    if entity is not None and entity.kind in {"class", "struct", "union"}:
        member_access = "private" if entity.kind == "class" else "public"
    for child in children:
        if not isinstance(child, dict):
            continue
        child_kind = child.get("kind")
        if child_kind == "AccessSpecDecl":
            child_access = child.get("access")
            if isinstance(child_access, str) and child_access:
                member_access = child_access
            continue
        if child_kind in {"FullComment", "ParagraphComment", "TextComment", "ParmVarDecl", "CXXBaseSpecifier"}:
            continue
        _walk_ast(
            child,
            graph=graph,
            project_root=project_root,
            public_roots=public_roots,
            inherited_file=path,
            parent_entity=next_parent,
            scopes=next_scopes,
            template_context=next_template,
            access=member_access,
            file_state=file_state,
        )


def _compile_entry_arguments(entry: dict[str, object]) -> list[str]:
    arguments = entry.get("arguments")
    if isinstance(arguments, list) and all(isinstance(value, str) for value in arguments):
        return list(arguments)
    command = entry.get("command")
    if isinstance(command, str):
        return shlex.split(command)
    return []


def _choose_compile_entry(entries: list[dict[str, object]]) -> dict[str, object] | None:
    preferred = {".cc", ".cpp", ".cxx", ".c++", ".C"}
    for entry in entries:
        source = entry.get("file")
        if isinstance(source, str) and Path(source).suffix in preferred:
            return entry
    return entries[0] if entries else None


def _frontend_arguments(
    entry: dict[str, object] | None,
    *,
    public_roots: tuple[Path, ...],
    predefines: Iterable[str],
) -> tuple[Path | None, list[str]]:
    if entry is None:
        args = ["-std=c++20"]
        directory = None
    else:
        raw = _compile_entry_arguments(entry)
        directory_value = entry.get("directory")
        directory = Path(directory_value) if isinstance(directory_value, str) else None
        args = raw[1:] if raw else []

        source = entry.get("file")
        source_values = {str(source)} if isinstance(source, str) else set()
        if isinstance(source, str) and directory is not None:
            source_values.add(str((directory / source).resolve()))

        cleaned: list[str] = []
        skip_next = False
        options_with_value = {"-o", "-MF", "-MT", "-MQ", "--serialize-diagnostics"}
        for argument in args:
            if skip_next:
                skip_next = False
                continue
            if argument in options_with_value:
                skip_next = True
                continue
            if argument in {"-c", "-MD", "-MMD", "-MP"}:
                continue
            if argument in source_values:
                continue
            try:
                if source_values and str(Path(argument).resolve()) in source_values:
                    continue
            except OSError:
                pass
            if argument.startswith("-o") and len(argument) > 2:
                continue
            cleaned.append(argument)
        args = cleaned

    for root in public_roots:
        args.append(f"-I{root}")
    names: set[str] = set()
    for value in predefines:
        if not value:
            continue
        args.append(f"-D{value}")
        names.add(value.split("=", 1)[0])
    if "__CUDACC__" in names or "__HIPCC__" in names:
        args.extend(["-D__host__=", "-D__device__=", "-D__global__="])
    return directory, args


def _public_headers(public_roots: Iterable[Path]) -> list[Path]:
    suffixes = {".h", ".hh", ".hpp", ".hxx", ".cuh"}
    values: set[Path] = set()
    for root in public_roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in suffixes:
                values.add(path.resolve())
    return sorted(values)


def _write_umbrella(path: Path, headers: Iterable[Path]) -> None:
    lines = ["// Generated by BESA for semantic API extraction."]
    for header in headers:
        escaped = header.as_posix().replace('"', '\\"')
        lines.append(f'#include "{escaped}"')
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _include_guard_name(lines: list[str]) -> str | None:
    """Recognize the conventional #ifndef/#define include-guard pair near the file start."""

    ifndef = re.compile(r"^\s*#\s*ifndef\s+([A-Za-z_][A-Za-z0-9_]*)\s*$")
    define = re.compile(r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\b")
    candidate: str | None = None
    for line in lines[:40]:
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue
        if candidate is None:
            match = ifndef.match(line)
            if match is None:
                if stripped.startswith("#pragma once"):
                    return None
                continue
            candidate = match.group(1)
            continue
        match = define.match(line)
        if match is not None:
            return candidate if match.group(1) == candidate else None
        if not stripped.startswith("#"):
            return None
    return None


def _macro_candidates(
    headers: Iterable[Path],
    project_root: Path,
    public_roots: tuple[Path, ...],
    active_definitions: dict[str, str],
) -> list[ApiEntity]:
    entities: list[ApiEntity] = []
    define = re.compile(r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)(\([^\n]*?\))?(?:\s+(.*))?$")
    comment_lines: list[str] = []
    for header in headers:
        try:
            lines = header.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        include_guard = _include_guard_name(lines)
        for number, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("///"):
                comment_lines.append(stripped[3:].strip())
                continue
            match = define.match(line)
            if match:
                name = match.group(1)
                if name == include_guard:
                    comment_lines.clear()
                    continue
                args = match.group(2) or ""
                value = (match.group(3) or "").strip()
                candidate_tail = " ".join((args + ((" " + value) if value else "")).split())
                active_tail = active_definitions.get(name)
                if active_tail is None or candidate_tail != active_tail:
                    comment_lines.clear()
                    continue
                parameters: tuple[ApiParameter, ...] = ()
                if args:
                    names = [item.strip() for item in args[1:-1].split(",") if item.strip()]
                    parameters = tuple(ApiParameter(item) for item in names)
                entity = ApiEntity(
                    id=stable_entity_id("cpp", "macro", name),
                    language="cpp",
                    kind="macro",
                    name=name,
                    qualified_name=name,
                    signatures=[ApiSignature(parameters=parameters, spelling=line.strip())],
                    documentation=" ".join(comment_lines).strip(),
                    source=SourceLocation(
                        _logical_public_path(header, public_roots, project_root), number, 1
                    ),
                    properties=[value] if value else [],
                )
                entities.append(entity)
                comment_lines.clear()
                continue
            if stripped and not stripped.startswith("//"):
                comment_lines.clear()
    return entities


def _active_macro_definitions(
    *,
    clang_executable: str,
    frontend_args: list[str],
    umbrella: Path,
    cwd: Path,
) -> dict[str, str]:
    """Return macro definitions active under the exact semantic extraction configuration."""

    result = subprocess.run(
        [clang_executable, *frontend_args, "-dM", "-E", str(umbrella)],
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError("Clang preprocessor macro discovery failed:\n" + result.stderr.strip())
    pattern = re.compile(r"^#define\s+([A-Za-z_][A-Za-z0-9_]*)(.*)$")
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        match = pattern.match(line)
        if match is not None:
            values[match.group(1)] = " ".join(match.group(2).strip().split())
    return values


def extract_cpp_graph(
    *,
    project: str,
    version: str,
    project_root: Path,
    build_directory: Path,
    public_roots: Iterable[Path],
    profile_name: str,
    predefines: Iterable[str] = (),
    clang_executable: str = "clang++",
    work_directory: Path,
) -> ApiGraph:
    """Extract one configured C++ API surface with Clang's semantic frontend."""

    roots = tuple(path.resolve() for path in public_roots if path.is_dir())
    headers = _public_headers(roots)
    graph = ApiGraph(project=project, version=version, language="cpp")
    graph.variants[profile_name] = {"predefined": list(predefines)}
    for header in headers:
        try:
            graph.sources[_logical_public_path(header, roots, project_root)] = header.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            pass
    if not headers:
        return graph

    database = build_directory / "compile_commands.json"
    entries: list[dict[str, object]] = []
    if database.is_file():
        try:
            raw_entries = json.loads(database.read_text(encoding="utf-8"))
            if isinstance(raw_entries, list):
                entries = [entry for entry in raw_entries if isinstance(entry, dict)]
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Cannot read compilation database {database}: {error}") from error

    work_directory.mkdir(parents=True, exist_ok=True)
    umbrella = work_directory / "besa-api.cpp"
    _write_umbrella(umbrella, headers)
    cwd, frontend_args = _frontend_arguments(
        _choose_compile_entry(entries), public_roots=roots, predefines=predefines
    )

    command = [
        clang_executable,
        *frontend_args,
        "-fparse-all-comments",
        "-Wno-unknown-warning-option",
        "-Wno-ignored-attributes",
        "-Xclang",
        "-ast-dump=json",
        "-fsyntax-only",
        str(umbrella),
    ]
    result = subprocess.run(
        command,
        cwd=cwd or project_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Clang semantic API extraction failed for profile "
            f"{profile_name!r}:\n{result.stderr.strip()}"
        )
    try:
        tree = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Clang returned invalid AST JSON for profile {profile_name!r}: {error}"
        ) from error
    if not isinstance(tree, dict):
        raise RuntimeError(f"Clang returned an unexpected AST root for profile {profile_name!r}")

    _walk_ast(
        tree,
        graph=graph,
        project_root=project_root,
        public_roots=roots,
        file_state=[None],
    )

    # The semantic AST deliberately does not represent macros as declarations. Discover only the
    # source macros that are active under this exact Clang configuration so conditional macros get
    # the same profile-aware availability semantics as declarations.
    active_macros = _active_macro_definitions(
        clang_executable=clang_executable,
        frontend_args=frontend_args,
        umbrella=umbrella,
        cwd=cwd or project_root,
    )
    for entity in _macro_candidates(headers, project_root, roots, active_macros):
        graph.add(entity)

    for entity in graph.entities.values():
        if profile_name not in entity.variants:
            entity.variants.append(profile_name)
    graph.rebuild_children()
    return graph
