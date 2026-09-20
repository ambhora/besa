# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
"""ProperDocs source generation for BESA's code-oriented API layout."""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
from pathlib import Path

from .model import ApiEntity, ApiGraph, ApiSignature, entity_sort_key


def _segments(entity: ApiEntity) -> list[str]:
    separator = "." if entity.language == "python" else "::"
    return [part for part in entity.qualified_name.split(separator) if part]


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-.").lower()
    if not cleaned:
        cleaned = "symbol"
    if cleaned != value.lower():
        digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:7]
        cleaned = f"{cleaned}-{digest}"
    return cleaned


def entity_document(entity: ApiEntity) -> Path:
    parts = [_slug(part) for part in _segments(entity)]
    if entity.kind in {"namespace", "module", "package"}:
        return Path("api", *parts, "index.md")
    if len(parts) > 1:
        return Path("api", *parts[:-1], f"{entity.kind}-{parts[-1]}.md")
    return Path("api", f"{entity.kind}-{parts[0]}.md")


def entity_url(entity: ApiEntity) -> str:
    path = entity_document(entity).with_suffix("")
    if path.name == "index":
        path = path.parent
    return "/".join(path.parts) + "/"


def _source_document(source_path: str) -> Path:
    logical = Path(source_path)
    return Path("_sources", *logical.parent.parts, logical.name + ".md")


def _source_page(source_path: str, content: str) -> str:
    title = Path(source_path).name
    lines = [f"# File {title}", "", f"`{source_path}`", "", '<pre class="besa-api-source-code"><code>']
    source_lines = content.splitlines()
    for number, value in enumerate(source_lines, 1):
        lines.append(
            f'<span id="L{number}" data-line="{number}">{html.escape(value) or " "}</span>'
        )
    lines.extend(["</code></pre>", ""])
    return "\n".join(lines)


def _source_href(entity: ApiEntity, graph: ApiGraph) -> str | None:
    if entity.source is None or entity.source.path not in graph.sources:
        return None
    value = _relative_link(entity_document(entity), _source_document(entity.source.path))
    if entity.source.line:
        value += f"#L{entity.source.line}"
    return value


def _signature_label(entity: ApiEntity, signature: ApiSignature) -> str:
    return f"{entity.name}{signature.compact}" if entity.kind != "macro" else entity.name


def _parameter_spelling(signature: ApiSignature, language: str) -> str:
    if language != "python":
        values: list[str] = []
        for parameter in signature.parameters:
            value = parameter.type or parameter.name
            if parameter.name and parameter.type:
                value += f" {parameter.name}"
            if parameter.default is not None:
                value += f" = {parameter.default}"
            values.append(value)
        return ", ".join(values)

    values: list[str] = []
    parameters = list(signature.parameters)
    positional_only = [item for item in parameters if item.kind == "positional-only"]
    has_var_positional = any(item.kind == "var-positional" for item in parameters)
    keyword_marker_emitted = False
    for index, parameter in enumerate(parameters):
        if parameter.kind == "keyword-only" and not has_var_positional and not keyword_marker_emitted:
            values.append("*")
            keyword_marker_emitted = True
        prefix = ""
        if parameter.kind == "var-positional":
            prefix = "*"
            keyword_marker_emitted = True
        elif parameter.kind == "var-keyword":
            prefix = "**"
        value = prefix + parameter.name
        if parameter.type:
            value += f": {parameter.type}"
        if parameter.default is not None:
            value += f" = {parameter.default}"
        values.append(value)
        if positional_only and index + 1 == len(positional_only):
            values.append("/")
    return ", ".join(values)


def _signature_spelling(entity: ApiEntity, signature: ApiSignature) -> str:
    if signature.spelling:
        return signature.spelling
    parameters = _parameter_spelling(signature, entity.language)
    qualifiers = " ".join(signature.qualifiers)
    if entity.language == "python":
        prefix = "async def" if "async" in signature.qualifiers else "def"
        value = f"{prefix} {entity.qualified_name}({parameters})"
        if signature.returns:
            value += f" -> {signature.returns}"
        return value
    if entity.language == "rust":
        modifiers = [value for value in entity.properties if value != "pub"]
        prefix = "pub " + ((" ".join(modifiers) + " ") if modifiers else "")
        value = f"{prefix}fn {entity.qualified_name}({parameters})"
        if signature.returns:
            value += f" -> {signature.returns}"
        return value
    prefix_values = [value for value in entity.properties if value in {"inline", "constexpr", "consteval", "static", "virtual"}]
    prefix = (" ".join(prefix_values) + " ") if prefix_values else ""
    result = (signature.returns + " ") if signature.returns else ""
    suffix_values = [value for value in signature.qualifiers if value not in prefix_values]
    suffix = (" " + " ".join(suffix_values)) if suffix_values else ""
    return f"{prefix}{result}{entity.qualified_name}({parameters}){suffix}".strip()


def _paragraphs(text: str) -> str:
    if not text.strip():
        return '<p class="besa-api-undocumented">No API documentation has been provided.</p>'
    return "\n".join(
        f"<p>{html.escape(paragraph.strip())}</p>"
        for paragraph in re.split(r"\n\s*\n", text.strip())
        if paragraph.strip()
    )


def _badges(values: list[str]) -> str:
    if not values:
        return ""
    return " ".join(f'<span class="besa-api-badge">{html.escape(value)}</span>' for value in values)


def _entity_page(entity: ApiEntity, graph: ApiGraph) -> str:
    document_path = entity_document(entity)
    variants_link = _relative_link(document_path, Path("api-variants.md"))
    lines = [f"# {entity.name}", ""]
    if entity.source:
        location = entity.source.path
        if entity.source.line:
            location += f":{entity.source.line}"
        source_href = _source_href(entity, graph)
        if source_href:
            label = f"File {Path(entity.source.path).name}"
            lines.extend(
                [
                    '<p class="besa-api-defined">Defined in '
                    f'<a href="{html.escape(source_href)}">{html.escape(label)}</a></p>',
                    "",
                ]
            )
        else:
            lines.extend([f'<p class="besa-api-defined">Defined in <code>{html.escape(location)}</code></p>', ""])

    signatures = entity.signatures or [ApiSignature()]
    for index, signature in enumerate(signatures):
        label = _signature_label(entity, signature) if entity.signatures else entity.navigation_label
        lines.extend([f"## {label}", ""])
        lines.append('<article class="besa-api-entity-card">')
        lines.append(
            '<pre class="besa-api-declaration"><code>'
            + html.escape(_signature_spelling(entity, signature))
            + "</code></pre>"
        )
        properties = list(dict.fromkeys([*entity.properties, *signature.qualifiers]))
        if properties:
            lines.append(
                '<div class="besa-api-meta-row"><strong>Properties</strong><span>'
                + _badges(properties)
                + "</span></div>"
            )
        if entity.source:
            location = entity.source.path
            if entity.source.line:
                location += f":{entity.source.line}"
            source_href = _source_href(entity, graph)
            definition = (
                f'<a href="{html.escape(source_href)}"><code>{html.escape(location)}</code></a>'
                if source_href
                else f"<code>{html.escape(location)}</code>"
            )
            lines.append(
                '<div class="besa-api-meta-row"><strong>Definition</strong>'
                + definition
                + "</div>"
            )
        if entity.bases:
            lines.append(
                '<div class="besa-api-meta-row"><strong>Bases</strong><span>'
                + " · ".join(f"<code>{html.escape(base)}</code>" for base in entity.bases)
                + "</span></div>"
            )
        lines.append('<div class="besa-api-description">' + _paragraphs(entity.documentation) + "</div>")
        if entity.variants:
            lines.append(
                '<div class="besa-api-variants"><strong>API variants</strong><span>'
                + " · ".join(
                    f'<a href="{html.escape(variants_link)}">{html.escape(value)}</a>'
                    for value in entity.variants
                )
                + "</span></div>"
            )
        lines.append("</article>")
        lines.append("")

    if entity.children:
        lines.extend(["## Members", "", '<div class="besa-api-member-grid">'])
        for child_id in entity.children:
            child = graph.entities[child_id]
            relative = _relative_link(entity_document(entity), entity_document(child))
            lines.append(
                f'<a class="besa-api-member" href="{html.escape(relative)}">'
                f'<span class="api-kind" data-kind="{html.escape(child.kind)}"></span>'
                f'<code>{html.escape(child.navigation_label)}</code></a>'
            )
        lines.extend(["</div>", ""])
    return "\n".join(lines)


def _relative_link(source: Path, target: Path) -> str:
    source_dir = source.parent
    import posixpath

    value = posixpath.relpath(target.with_suffix("").as_posix(), source_dir.as_posix())
    if value.endswith("/index"):
        value = value[:-6]
    return value + "/"


def _variant_page(graph: ApiGraph) -> str:
    lines = [
        "# API Variants and Features",
        "",
        "API variants describe the configured forms in which an API entity exists. Each row below is one concrete build configuration used for semantic extraction.",
        "",
        "| Variant | Profile | Features | Parser Predefinitions |",
        "| --- | --- | --- | --- |",
    ]
    for name, metadata in graph.variants.items():
        profile = str(metadata.get("profile", name))
        features = metadata.get("features", [])
        predefined = metadata.get("predefined", [])
        feature_text = ", ".join(f"`{value}`" for value in features) if isinstance(features, list) and features else "—"
        predefined_text = ", ".join(f"`{value}`" for value in predefined) if isinstance(predefined, list) and predefined else "—"
        lines.append(f"| `{name}` | `{profile}` | {feature_text} | {predefined_text} |")
    lines.append("")
    return "\n".join(lines)


def _home_page(graph: ApiGraph) -> str:
    roots = graph.roots()
    lines = [
        "# API Documentation Home",
        "",
        f"Semantic API reference for **{graph.project}** {graph.version}.",
        "",
        "The reference is extracted into a language-neutral BESA API graph and rendered with the same code-oriented layout across supported languages.",
        "",
        "## Outline",
        "",
    ]
    for entity in roots:
        lines.append(f"- [{entity.navigation_label}]({entity_url(entity)})")
    lines.append("")
    return "\n".join(lines)


def _kind_marker(kind: str) -> str:
    return {
        "namespace": "N",
        "module": "M",
        "package": "P",
        "class": "C",
        "struct": "S",
        "union": "U",
        "enum": "E",
        "trait": "T",
        "protocol": "P",
        "function": "F",
        "method": "F",
        "constructor": "F",
        "type_alias": "T",
        "variable": "V",
        "attribute": "A",
        "property": "P",
        "constant": "C",
        "macro": "M",
        "concept": "C",
    }.get(kind, "·")


def _nav_entity(entity: ApiEntity, graph: ApiGraph, indent: int) -> list[str]:
    pad = "  " * indent
    label = entity.navigation_label
    document = entity_document(entity).as_posix()
    if not entity.children:
        return [f"{pad}- {json.dumps(label)}: {json.dumps(document)}"]
    lines = [f"{pad}- {json.dumps(label)}:"]
    lines.append(f"{pad}  - {json.dumps(label)}: {json.dumps(document)}")
    for child_id in entity.children:
        lines.extend(_nav_entity(graph.entities[child_id], graph, indent + 1))
    return lines


def _properdocs_config(
    graph: ApiGraph,
    *,
    source_directory: Path,
    output_directory: Path,
    template_directory: Path,
    copyright_text: str,
) -> str:
    lines = [
        f"site_name: {json.dumps(graph.project + ' API documentation')}",
        f"site_description: {json.dumps('API reference for ' + graph.project)}",
        f"docs_dir: {json.dumps(str(source_directory))}",
        f"site_dir: {json.dumps(str(output_directory))}",
        f"copyright: {json.dumps(copyright_text)}",
        "",
        "extra:",
        "  generator: false",
        "",
        "theme:",
        "  name: materialx",
        "  palette:",
        "    - scheme: default",
        "      primary: custom",
        "      accent: custom",
        "    - scheme: slate",
        "      primary: custom",
        "      accent: custom",
        "  features:",
        "    - navigation.indexes",
        "    - navigation.sections",
        "    - navigation.top",
        "    - search.highlight",
        "    - search.suggest",
        "    - toc.follow",
        "",
        "extra_css:",
        "  - assets/stylesheets/besa-api.css",
        "extra_javascript:",
        "  - assets/javascripts/besa-api-config.js",
        "  - assets/javascripts/besa-api.js",
        "",
        "nav:",
        '  - "Home": "index.md"',
        '  - "API Variants and Features": "api-variants.md"',
    ]
    for entity in graph.roots():
        lines.extend(_nav_entity(entity, graph, 1))
    lines.append("")
    return "\n".join(lines)


def _symbol_alias_document(entity: ApiEntity, alias_document: Path) -> str:
    target = _relative_link(alias_document, entity_document(entity))
    # The semantic aliases are intentionally tiny stable pages. ProperDocs' main-site hook checks
    # for their existence before resolving @apidocs:: references.
    return "\n".join(
        [
            f"# {entity.qualified_name}",
            "",
            f'<meta http-equiv="refresh" content="0; url={html.escape(target)}">',
            "",
            f"[{entity.qualified_name}]({target})",
            "",
        ]
    )


def render_properdocs_source(
    graph: ApiGraph,
    *,
    source_directory: Path,
    output_directory: Path,
    template_directory: Path,
    project_docs_url: str,
    copyright_text: str,
) -> Path:
    shutil.rmtree(source_directory, ignore_errors=True)
    source_directory.mkdir(parents=True)
    (source_directory / "index.md").write_text(_home_page(graph), encoding="utf-8")
    (source_directory / "api-variants.md").write_text(_variant_page(graph), encoding="utf-8")

    for entity in graph.entities.values():
        document = source_directory / entity_document(entity)
        document.parent.mkdir(parents=True, exist_ok=True)
        document.write_text(_entity_page(entity, graph), encoding="utf-8")

        separator = "." if entity.language == "python" else "::"
        symbol = Path(*entity.qualified_name.split(separator))
        alias_document = Path("_symbols", *symbol.parts, "index.md")
        alias = source_directory / alias_document
        alias.parent.mkdir(parents=True, exist_ok=True)
        alias.write_text(_symbol_alias_document(entity, alias_document), encoding="utf-8")

    for source_path, content in graph.sources.items():
        source_document = source_directory / _source_document(source_path)
        source_document.parent.mkdir(parents=True, exist_ok=True)
        source_document.write_text(_source_page(source_path, content), encoding="utf-8")

    assets_source = template_directory / "assets"
    if assets_source.is_dir():
        shutil.copytree(assets_source, source_directory / "assets", dirs_exist_ok=True)

    config_js = source_directory / "assets" / "javascripts" / "besa-api-config.js"
    config_js.parent.mkdir(parents=True, exist_ok=True)
    config_js.write_text(
        "window.BESA_API_CONFIG = "
        + json.dumps(
            {
                "project": graph.project,
                "version": graph.version,
                "projectDocsUrl": project_docs_url,
                "apiRootUrl": "../" * (2 + max(1, len(Path(graph.version).parts))),
                "entityKinds": {entity_url(entity): entity.kind for entity in graph.entities.values()},
            },
            sort_keys=True,
        )
        + ";\n",
        encoding="utf-8",
    )

    config = source_directory.parent / "properdocs.yml"
    config.write_text(
        _properdocs_config(
            graph,
            source_directory=source_directory,
            output_directory=output_directory,
            template_directory=template_directory,
            copyright_text=copyright_text,
        ),
        encoding="utf-8",
    )
    return config
