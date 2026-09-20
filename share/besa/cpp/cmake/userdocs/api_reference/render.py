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

try:
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import CppLexer, PythonLexer, RustLexer, TextLexer
except ImportError:  # pragma: no cover - optional dependency in some bootstrap environments
    highlight = None
    HtmlFormatter = None
    CppLexer = PythonLexer = RustLexer = TextLexer = None

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
    if entity.kind in {"class", "struct", "union", "enum", "trait", "protocol"}:
        if len(parts) > 1:
            return Path("api", *parts[:-1], f"{entity.kind}-{parts[-1]}", "index.md")
        return Path("api", f"{entity.kind}-{parts[0]}", "index.md")
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


def _highlight_code(code: str, language: str) -> str:
    if highlight is None or HtmlFormatter is None:
        return html.escape(code)

    lexer_map = {
        "cpp": CppLexer,
        "python": PythonLexer,
        "rust": RustLexer,
    }
    lexer_type = lexer_map.get(language, TextLexer)
    assert lexer_type is not None
    # Inline styles make generated declaration fragments self-contained.  ProperDocs owns the
    # surrounding code theme, while the language tokens remain highlighted even when the API site
    # is mounted below another site's URL prefix.
    formatter = HtmlFormatter(nowrap=True, noclasses=True)
    return highlight(code, lexer_type(), formatter)


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


def _entity_declaration(entity: ApiEntity) -> str:
    if entity.language == "python":
        if entity.kind in {"class", "protocol"}:
            bases = f"({', '.join(entity.bases)})" if entity.bases else ""
            return f"class {entity.qualified_name}{bases}"
        if entity.kind in {"module", "package"}:
            return f"module {entity.qualified_name}"
        if entity.kind == "type_alias":
            target = next((value[2:] for value in entity.properties if value.startswith("= ")), "")
            return f"{entity.qualified_name} = {target}".rstrip()
        return entity.qualified_name

    if entity.language == "rust":
        prefix = "pub " if "pub" in entity.properties else ""
        keyword = {
            "struct": "struct",
            "enum": "enum",
            "trait": "trait",
            "module": "mod",
            "type_alias": "type",
            "constant": "const",
        }.get(entity.kind, entity.kind)
        return f"{prefix}{keyword} {entity.qualified_name}".strip()

    if entity.kind == "namespace":
        return f"namespace {entity.qualified_name}"
    if entity.kind in {"class", "struct", "union"}:
        bases = f" : {', '.join(entity.bases)}" if entity.bases else ""
        return f"{entity.kind} {entity.qualified_name}{bases}"
    if entity.kind == "enum":
        scoped = " class" if "scoped" in entity.properties else ""
        return f"enum{scoped} {entity.qualified_name}"
    if entity.kind == "type_alias":
        target = next((value[2:] for value in entity.properties if value.startswith("= ")), "")
        return f"using {entity.qualified_name} = {target}".rstrip()
    if entity.kind in {"attribute", "variable", "constant"}:
        type_name = next((value for value in entity.properties if not value.startswith("=")), "")
        return f"{type_name} {entity.qualified_name}".strip()
    if entity.kind == "concept":
        return f"concept {entity.qualified_name}"
    if entity.kind == "macro" and entity.signatures:
        return entity.signatures[0].spelling or entity.name
    return entity.qualified_name


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


def _variant_anchor(name: str) -> str:
    return "variant-" + _slug(name)


def _resolve_related_entity(reference: str, entity: ApiEntity, graph: ApiGraph) -> ApiEntity | None:
    normalized = reference.strip()
    if not normalized:
        return None

    if "::" in normalized or "." in normalized:
        for candidate in graph.entities.values():
            if candidate.qualified_name == normalized or candidate.name == normalized:
                return candidate

    if entity.parent and entity.parent in graph.entities:
        parent = graph.entities[entity.parent]
        for child_id in parent.children:
            child = graph.entities[child_id]
            if child.name == normalized:
                return child

    matches = [candidate for candidate in graph.entities.values() if candidate.name == normalized]
    return matches[0] if len(matches) == 1 else None


def _documentation_blocks(entity: ApiEntity, graph: ApiGraph) -> tuple[str, list[tuple[str, ApiEntity | None]]]:
    related_names = list(entity.related)
    paragraphs: list[str] = []
    for block in re.split(r"\n\s*\n", entity.documentation.strip()):
        paragraph = block.strip()
        if not paragraph:
            continue
        if paragraph.startswith("BESA-API-RELATES-TO:"):
            payload = paragraph.split(":", 1)[1]
            for item in re.split(r"\s*,\s*", payload.strip()):
                if item and item not in related_names:
                    related_names.append(item)
            continue
        paragraphs.append(paragraph)
    text = "\n\n".join(paragraphs)
    related = [
        (name, _resolve_related_entity(name, entity, graph))
        for name in related_names
    ]
    return _paragraphs(text), related


def _variant_display_name(name: str) -> str:
    if name.casefold() in {"cpu", "cuda", "hip", "mpi", "sycl"}:
        return name.upper()
    return name


def _profile_reference(name: str, document_path: Path) -> str:
    href = _relative_link(document_path, Path("api-variants.md")) + f"#{_variant_anchor(name)}"
    return f'<a href="{html.escape(href)}">{html.escape(_variant_display_name(name))}</a>'


def _variant_explainer(document_path: Path) -> str:
    href = _relative_link(document_path, Path("api-variants.md")) + "#api-variants"
    return f'<a href="{html.escape(href)}">About API variants and features</a>'


def _member_signature_spelling(entity: ApiEntity, signature: ApiSignature) -> str:
    parameters = _parameter_spelling(signature, entity.language)
    if entity.language == "python":
        prefix = "async def" if "async" in signature.qualifiers else "def"
        value = f"{prefix} {entity.name}({parameters})"
        if signature.returns:
            value += f" -> {signature.returns}"
        return value
    if entity.language == "rust":
        value = f"fn {entity.name}({parameters})"
        if signature.returns:
            value += f" -> {signature.returns}"
        return value
    prefix_values = [
        value
        for value in entity.properties
        if value in {"inline", "constexpr", "consteval", "static", "virtual"}
    ]
    prefix = (" ".join(prefix_values) + " ") if prefix_values else ""
    result = (signature.returns + " ") if signature.returns else ""
    suffix_values = [value for value in signature.qualifiers if value not in prefix_values]
    suffix = (" " + " ".join(suffix_values)) if suffix_values else ""
    return f"{prefix}{result}{entity.name}({parameters}){suffix}".strip()


def _member_summary_spelling(entity: ApiEntity) -> str:
    if entity.kind in {"attribute", "variable", "constant"}:
        type_name = next((value for value in entity.properties if not value.startswith("=")), "")
        return f"{type_name} {entity.name}".strip()
    if entity.kind == "type_alias":
        target = next((value[2:] for value in entity.properties if value.startswith("= ")), "")
        return f"using {entity.name} = {target}".rstrip()
    if entity.kind in {"class", "struct", "union", "enum", "trait", "protocol"}:
        return f"{entity.kind} {entity.name}"
    return entity.name


def _member_group_title(parent: ApiEntity, child: ApiEntity) -> str:
    class_like = parent.kind in {"class", "struct", "union", "trait", "protocol"}
    if child.kind in {"method", "constructor", "function"}:
        return "Public Functions" if class_like else "Functions"
    if child.kind in {"attribute", "property", "variable", "constant"}:
        return "Public Members" if class_like else "Variables"
    if child.kind in {"class", "struct", "union", "enum", "trait", "protocol", "type_alias", "concept"}:
        return "Public Types" if class_like else "Types"
    if child.kind in {"namespace", "module", "package"}:
        return "Namespaces"
    if child.kind == "macro":
        return "Macros"
    return "Members"


def _member_sections(entity: ApiEntity, graph: ApiGraph, document_path: Path) -> list[str]:
    groups: dict[str, list[ApiEntity]] = {}
    for child_id in entity.children:
        child = graph.entities[child_id]
        groups.setdefault(_member_group_title(entity, child), []).append(child)

    preferred = [
        "Public Types",
        "Public Functions",
        "Public Members",
        "Namespaces",
        "Types",
        "Functions",
        "Variables",
        "Macros",
        "Members",
    ]
    lines: list[str] = []
    for title in preferred:
        children = groups.get(title)
        if not children:
            continue
        lines.extend([f"## {title}", "", '<div class="besa-api-member-list">'])
        for child in children:
            href = _relative_link(document_path, entity_document(child))
            signatures = child.signatures if child.kind in {"function", "method", "constructor"} else []
            spellings = (
                [_member_signature_spelling(child, signature) for signature in signatures]
                if signatures
                else [_member_summary_spelling(child)]
            )
            for spelling in spellings:
                lines.append(
                    f'<a class="besa-api-member-detail" href="{html.escape(href)}">'
                    f'<span class="api-kind" data-kind="{html.escape(child.kind)}"></span>'
                    f'<code class="language-{html.escape(child.language)}">'
                    + _highlight_code(spelling, child.language)
                    + "</code></a>"
                )
        lines.extend(["</div>", ""])
    return lines


def _entity_page(entity: ApiEntity, graph: ApiGraph) -> str:
    document_path = entity_document(entity)
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
            lines.extend(
                [f'<p class="besa-api-defined">Defined in <code>{html.escape(location)}</code></p>', ""]
            )

    callable_entity = entity.kind in {"function", "method", "constructor", "macro"}
    variants = entity.signatures if callable_entity and entity.signatures else [None]
    for signature in variants:
        if signature is not None:
            label = _signature_label(entity, signature)
            declaration = _signature_spelling(entity, signature)
            signature_properties = list(signature.qualifiers)
        else:
            label = entity.name
            declaration = _entity_declaration(entity)
            signature_properties = []

        lines.extend([f"## {label}", ""])
        lines.append('<article class="besa-api-entity-card">')
        lines.append(
            '<pre class="besa-api-declaration"><code class="language-'
            + html.escape(entity.language)
            + '">'
            + _highlight_code(declaration, entity.language)
            + "</code></pre>"
        )
        properties = list(dict.fromkeys([*entity.properties, *signature_properties]))
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

        description_html, related = _documentation_blocks(entity, graph)
        lines.append('<div class="besa-api-description">' + description_html + "</div>")
        if related:
            values = []
            for text, target in related:
                if target is None:
                    values.append(f"<code>{html.escape(text)}</code>")
                else:
                    href = _relative_link(document_path, entity_document(target))
                    values.append(
                        f'<a href="{html.escape(href)}"><code>{html.escape(target.name)}</code></a>'
                    )
            lines.append(
                '<div class="besa-api-meta-row besa-api-related"><strong>Related:</strong><span>'
                + " · ".join(values)
                + "</span></div>"
            )
        if entity.variants:
            lines.append(
                '<div class="besa-api-variants"><strong>API variants</strong><span>'
                + " · ".join(_profile_reference(value, document_path) for value in entity.variants)
                + " · "
                + _variant_explainer(document_path)
                + "</span></div>"
            )
        lines.append("</article>")
        lines.append("")

    if entity.children:
        lines.extend(_member_sections(entity, graph, document_path))
    return "\n".join(lines)


def _relative_link(source: Path, target: Path) -> str:
    import posixpath

    def output_directory(document: Path) -> Path:
        if document.name == "index.md":
            return document.parent
        return document.with_suffix("")

    source_dir = output_directory(source)
    target_dir = output_directory(target)
    value = posixpath.relpath(target_dir.as_posix(), source_dir.as_posix())
    return ("./" if value == "." else value.rstrip("/") + "/")


def _variant_page(graph: ApiGraph) -> str:
    metadata = graph.metadata
    catalog = metadata.get("catalog", {}) if isinstance(metadata.get("catalog", {}), dict) else {}
    manifests = metadata.get("variant_manifests", {}) if isinstance(metadata.get("variant_manifests", {}), dict) else {}
    documentation_inputs = metadata.get("documentation_inputs", []) if isinstance(metadata.get("documentation_inputs", []), list) else []
    variant_names = list(graph.variants)

    declared = catalog.get("declared_features", [])
    declared_features = [str(name) for name in declared] if isinstance(declared, list) else []
    model = catalog.get("project_model", {}) if isinstance(catalog.get("project_model", {}), dict) else {}
    feature_table = model.get("features", {}) if isinstance(model.get("features", {}), dict) else {}
    if not declared_features:
        declared_features = [str(name) for name in feature_table]
    if not declared_features:
        seen_features: set[str] = set()
        for value in graph.variants.values():
            features = value.get("features", []) if isinstance(value, dict) else []
            if isinstance(features, list):
                seen_features.update(str(feature) for feature in features)
        declared_features = sorted(seen_features)

    active_features = catalog.get("active_features", []) if isinstance(catalog.get("active_features", []), list) else []

    lines = [
        "# API Variants and Features",
        "",
        "API variants describe the different forms in which an individual API entity can occur in the source code. The same function, type, macro, or other entity may, for example, have CPU, CUDA, and HIP variants with different declarations or annotations.",
        "",
        "Features determine which variants of an entity can be present in a particular build. A declared variant label associates a name with the feature prerequisites and optional parser predefinitions needed to expose that form to the language parser. The variant belongs to the entity; the feature set is only the context used to discover it.",
        "",
        "The generated reference merges the declarations discovered under all variant conditions into one site. Each entity's API variants field shows the variants in which that entity exists, allowing feature-dependent forms to be documented together.",
        "",
        "## Overview",
        "",
        "| Item | Value |",
        "| --- | --- |",
        f"| Project | `{graph.project}` |",
        f"| Variant labels | {' · '.join(f'`{_variant_display_name(name)}`' for name in variant_names) or '—'} |",
        "| Reference model | Combined view of all discovered entity variants |",
        "| Manifest schema | `1` |",
        "",
        "## Variant selection by feature",
        "",
        "The table below shows the feature prerequisites associated with each variant label. `Documentation build` marks the features active in the build that is producing this site. The remaining columns show which features are required when discovering each variant. Features may therefore influence which form of an individual entity is active.",
        "",
        "| Feature | Documentation build | " + " | ".join(_variant_display_name(name) for name in variant_names) + " |",
        "| --- | --- | " + " | ".join("---" for _ in variant_names) + " |",
    ]
    for feature in declared_features:
        row = [f"`{feature}`", "yes" if feature in active_features else "—"]
        for name in variant_names:
            variant = graph.variants.get(name, {})
            features = variant.get("features", []) if isinstance(variant, dict) else []
            row.append("yes" if isinstance(features, list) and feature in features else "—")
        lines.append("| " + " | ".join(row) + " |")

    lines.extend([
        "",
        "## API Variants",
        "",
        "Each name below is a variant label that may occur on individual API entities. An entity may be available in one, several, or all declared variants.",
        "",
        "`Features` lists the feature prerequisites used to discover the variant. `Parser predefinitions` lists parser-only preprocessor symbols used to expose conditional declarations for that variant. They do not define a separate complete API surface.",
        "",
    ])
    for name, variant_metadata in graph.variants.items():
        profile = str(variant_metadata.get("profile", name)) if isinstance(variant_metadata, dict) else name
        features = variant_metadata.get("features", []) if isinstance(variant_metadata, dict) else []
        predefined = variant_metadata.get("predefined", []) if isinstance(variant_metadata, dict) else []
        lines.extend(
            [
                f'<a id="{_variant_anchor(name)}"></a>',
                f"### {_variant_display_name(name)}",
                "",
                "This label identifies one possible form of an API entity. The feature prerequisites and parser predefinitions below are used to discover declarations belonging to that variant.",
                "",
                "**Features**  ",
                (' · '.join(f'`{value}`' for value in features) if isinstance(features, list) and features else 'none'),
                "",
                "**Parser predefinitions**  ",
                (' · '.join(f'`{value}`' for value in predefined) if isinstance(predefined, list) and predefined else 'none'),
                "",
            ]
        )

    registrations: dict[tuple[str, ...], dict[str, object]] = {}
    selected_by_variant: dict[tuple[str, ...], list[str]] = {}
    catalog_registrations = catalog.get("registrations", []) if isinstance(catalog.get("registrations", []), list) else []
    for item in catalog_registrations:
        if not isinstance(item, dict):
            continue
        key = tuple(str(item.get(field, "")) for field in ("kind", "name", "path", "base", "language", "api"))
        registrations.setdefault(key, dict(item))
    for name, manifest in manifests.items():
        if not isinstance(manifest, dict):
            continue
        values = manifest.get("registrations", [])
        if not isinstance(values, list):
            continue
        for item in values:
            if not isinstance(item, dict):
                continue
            key = tuple(str(item.get(field, "")) for field in ("kind", "name", "path", "base", "language", "api"))
            registrations.setdefault(key, dict(item))
            if item.get("selected"):
                selected_by_variant.setdefault(key, []).append(name)

    if registrations:
        lines.extend([
            "## Registered project inputs",
            "",
            "These registrations come directly from the BESA project model and show which project inputs can contribute declarations to the generated API reference.",
            "",
            "`Name` is the registration name from the project model. `Kind` describes the kind of registered input, such as a source directory or generated include tree. `Path` is the registered location relative to the project. `API` indicates whether that input contributes to the public API reference or is documentation-only/disabled for API purposes. `Variants` shows which variant-discovery passes select that input.",
            "",
            "This section is useful when you want to understand why a declaration appears in the combined reference and which declared project input it came from.",
            "",
            "| Name | Kind | Path | API | Variants |",
            "| --- | --- | --- | --- | --- |",
        ])
        for key, registration in sorted(registrations.items(), key=lambda item: (str(item[1].get("path", "")), str(item[1].get("name", "")))):
            selected = selected_by_variant.get(key, [])
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{registration.get('name', '')}`",
                        f"`{registration.get('kind', '')}`",
                        f"`{registration.get('path', '')}`",
                        f"`{registration.get('api', '')}`",
                        " · ".join(f"`{_variant_display_name(value)}`" for value in selected) or "—",
                    ]
                )
                + " |"
            )

    if documentation_inputs:
        lines.extend([
            "",
            "## Documentation-only API inputs",
            "",
            "These inputs are added by the documentation layer rather than by ordinary BESA project registrations. They are typically used to expose developer-facing or test-support headers that should appear in the generated reference.",
            "",
            "`Path` is the staged include tree or source location added by the documentation pipeline. `Required feature` is the feature that must be active before this input is included in the generated reference. `Variants` shows which variant labels satisfy that feature requirement.",
            "",
            "They are shown separately so it is clear that these inputs do not yet come from the ordinary project registration model.",
            "",
            "| Path | Required feature | Variants |",
            "| --- | --- | --- |",
        ])
        for item in documentation_inputs:
            if not isinstance(item, dict):
                continue
            feature = str(item.get("feature", ""))
            selected = [
                name
                for name in variant_names
                if feature
                and isinstance(graph.variants.get(name, {}), dict)
                and feature in list(graph.variants.get(name, {}).get("features", []))
            ]
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{item.get('path', '')}`",
                        f"`{feature}`" if feature else "—",
                        " · ".join(f"`{_variant_display_name(value)}`" for value in selected) or "—",
                    ]
                )
                + " |"
            )

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
    # The first child is an index page.  ProperDocs/Material turns that into a clickable section
    # title when navigation.indexes is enabled, so class/namespace names remain both expandable and
    # directly navigable without an extra visible "Overview" row.
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
