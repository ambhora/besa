# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
"""Language-neutral API graph used by BESA's reference renderer."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class SourceLocation:
    path: str
    line: int | None = None
    column: int | None = None


@dataclass(frozen=True)
class ApiParameter:
    name: str
    type: str = ""
    default: str | None = None
    kind: str = ""


@dataclass(frozen=True)
class ApiSignature:
    parameters: tuple[ApiParameter, ...] = ()
    returns: str = ""
    qualifiers: tuple[str, ...] = ()
    spelling: str = ""

    @property
    def compact(self) -> str:
        values = [parameter.type or parameter.name or "?" for parameter in self.parameters]
        return f"({', '.join(values)})"


@dataclass
class ApiEntity:
    id: str
    language: str
    kind: str
    name: str
    qualified_name: str
    parent: str | None = None
    signatures: list[ApiSignature] = field(default_factory=list)
    documentation: str = ""
    source: SourceLocation | None = None
    properties: list[str] = field(default_factory=list)
    variants: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    bases: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)

    @property
    def navigation_label(self) -> str:
        if self.kind in {"function", "method", "constructor", "macro"}:
            if self.signatures:
                return f"{self.name}{self.signatures[0].compact}"
            if self.kind != "macro":
                return f"{self.name}()"
        return self.name


@dataclass
class ApiGraph:
    project: str
    version: str
    language: str
    entities: dict[str, ApiEntity] = field(default_factory=dict)
    variants: dict[str, dict[str, object]] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)

    def add(self, entity: ApiEntity) -> None:
        existing = self.entities.get(entity.id)
        if existing is None:
            self.entities[entity.id] = entity
            return

        for signature in entity.signatures:
            if signature not in existing.signatures:
                existing.signatures.append(signature)
        for value in entity.properties:
            if value not in existing.properties:
                existing.properties.append(value)
        for value in entity.variants:
            if value not in existing.variants:
                existing.variants.append(value)
        for value in entity.children:
            if value not in existing.children:
                existing.children.append(value)
        for value in entity.bases:
            if value not in existing.bases:
                existing.bases.append(value)
        for value in entity.aliases:
            if value not in existing.aliases:
                existing.aliases.append(value)
        if not existing.documentation and entity.documentation:
            existing.documentation = entity.documentation
        if existing.source is None and entity.source is not None:
            existing.source = entity.source

    def rebuild_children(self) -> None:
        for entity in self.entities.values():
            entity.children = []
        for entity in self.entities.values():
            if entity.parent and entity.parent in self.entities:
                parent = self.entities[entity.parent]
                if entity.id not in parent.children:
                    parent.children.append(entity.id)
        for entity in self.entities.values():
            entity.children.sort(key=lambda key: entity_sort_key(self.entities[key]))

    def roots(self) -> list[ApiEntity]:
        values = [
            entity
            for entity in self.entities.values()
            if not entity.parent or entity.parent not in self.entities
        ]
        return sorted(values, key=entity_sort_key)


def entity_sort_key(entity: ApiEntity) -> tuple[int, str, str]:
    order = {
        "package": 0,
        "module": 1,
        "namespace": 1,
        "class": 2,
        "struct": 2,
        "union": 2,
        "trait": 2,
        "protocol": 2,
        "enum": 3,
        "type_alias": 4,
        "constructor": 5,
        "method": 6,
        "function": 6,
        "property": 7,
        "attribute": 8,
        "variable": 8,
        "constant": 8,
        "macro": 9,
    }
    return (order.get(entity.kind, 50), entity.name.casefold(), entity.qualified_name)


def stable_entity_id(language: str, kind: str, qualified_name: str, signature_key: str = "") -> str:
    suffix = f"::{signature_key}" if signature_key else ""
    return f"{language}:{kind}:{qualified_name}{suffix}"


def relative_source_path(path: str | Path, project_root: Path) -> str:
    source = Path(path)
    try:
        return source.resolve().relative_to(project_root.resolve()).as_posix()
    except (OSError, ValueError):
        return source.as_posix()


def merge_graphs(graphs: Iterable[tuple[str, ApiGraph]], *, project: str, version: str, language: str) -> ApiGraph:
    merged = ApiGraph(project=project, version=version, language=language)
    for variant_name, graph in graphs:
        merged.variants[variant_name] = graph.variants.get(variant_name, {})
        for source_path, content in graph.sources.items():
            merged.sources.setdefault(source_path, content)
        for entity in graph.entities.values():
            entity_copy = ApiEntity(
                id=entity.id,
                language=entity.language,
                kind=entity.kind,
                name=entity.name,
                qualified_name=entity.qualified_name,
                parent=entity.parent,
                signatures=list(entity.signatures),
                documentation=entity.documentation,
                source=entity.source,
                properties=list(entity.properties),
                variants=list(entity.variants),
                children=list(entity.children),
                bases=list(entity.bases),
                aliases=list(entity.aliases),
            )
            if variant_name not in entity_copy.variants:
                entity_copy.variants.append(variant_name)
            merged.add(entity_copy)
    merged.rebuild_children()
    return merged
