// SPDX-FileCopyrightText: 2026 BESA developers
// SPDX-License-Identifier: Apache-2.0
(() => {
  "use strict";

  const prefixQualifiers = [
    "inline",
    "constexpr",
    "consteval",
    "static",
    "virtual",
    "explicit",
    "friend",
  ];

  const suffixPatterns = [
    /\bnoexcept(?:\s*\([^)]*\))?/g,
    /\bconst\b/g,
    /\bvolatile\b/g,
    /\boverride\b/g,
    /\bfinal\b/g,
    /(?:^|\s)(&&|&)(?=\s|$)/g,
  ];

  function normalizedText(element) {
    return ((element && element.textContent) || "").replace(/¶/g, "").replace(/\s+/g, " ").trim();
  }

  function qualifiersFor(signature) {
    const text = normalizedText(signature);
    const name = normalizedText(signature.querySelector(".sig-name"));
    const nameIndex = name ? text.indexOf(name) : -1;
    const beforeName = nameIndex >= 0 ? text.slice(0, nameIndex) : text;
    const closeParen = text.lastIndexOf(")");
    const afterParameters = closeParen >= 0 ? text.slice(closeParen + 1) : "";
    const result = [];

    for (const qualifier of prefixQualifiers) {
      if (new RegExp(`\\b${qualifier}\\b`).test(beforeName)) result.push(qualifier);
    }

    for (const pattern of suffixPatterns) {
      pattern.lastIndex = 0;
      for (const match of afterParameters.matchAll(pattern)) {
        const value = (match[1] || match[0]).trim();
        if (value && !result.includes(value)) result.push(value);
      }
    }

    return result;
  }

  function currentDocumentName() {
    const leaf = window.location.pathname.split("/").filter(Boolean).pop() || "index.html";
    return decodeURIComponent(leaf).replace(/\.html$/, "");
  }

  const sourceOccurrences = new Map();

  function functionSymbolFor(signature) {
    const pages = window.BESA_API_SOURCE_LOCATIONS || {};
    const page = pages[currentDocumentName()];
    if (!page || !page.symbols) return null;

    // Breathe preserves Doxygen's stable member id as a target span inside each declaration.  This
    // remains unique even when several overloads are embedded on one consolidated family page.
    const target = signature.querySelector("span.target[id]");
    if (!target) return null;
    return page.symbols[target.id] || null;
  }

  function legacyFunctionSourceLocationFor(signature) {
    const pages = window.BESA_API_SOURCE_LOCATIONS || {};
    const page = pages[currentDocumentName()];
    const name = normalizedText(signature.querySelector(".sig-name"));
    if (!page || !name || !page.functions || !page.functions[name]) return null;

    const occurrenceKey = `${currentDocumentName()}::${name}`;
    const occurrence = sourceOccurrences.get(occurrenceKey) || 0;
    sourceOccurrences.set(occurrenceKey, occurrence + 1);
    return page.functions[name][occurrence] || null;
  }

  function functionMetadataFor(signature) {
    const symbol = functionSymbolFor(signature);
    if (symbol) {
      return {
        source: symbol.source || null,
        qualifiers: Array.isArray(symbol.qualifiers) ? symbol.qualifiers : [],
      };
    }
    return { source: legacyFunctionSourceLocationFor(signature), qualifiers: [] };
  }

  function mergedQualifiers(...groups) {
    const result = [];
    for (const group of groups) {
      for (const qualifier of group || []) {
        if (qualifier && !result.includes(qualifier)) result.push(qualifier);
      }
    }
    return result;
  }

  function entitySourceLocation() {
    const pages = window.BESA_API_SOURCE_LOCATIONS || {};
    const page = pages[currentDocumentName()];
    return (page && page.entity) || null;
  }

  function propertyRow(qualifiers) {
    if (!qualifiers.length) return null;

    const row = document.createElement("div");
    row.className = "besa-api-qualifiers";
    row.setAttribute("aria-label", "Function properties");

    const label = document.createElement("span");
    label.className = "besa-api-properties-label";
    label.textContent = "Properties";
    row.appendChild(label);

    for (const qualifier of qualifiers) {
      const badge = document.createElement("span");
      badge.className = "besa-api-qualifier";
      badge.textContent = qualifier;
      row.appendChild(badge);
    }

    return row;
  }

  function sourceRow(source) {
    if (!source) return null;

    const row = document.createElement("div");
    row.className = "besa-api-source";

    const label = document.createElement("span");
    label.className = "besa-api-source-label";
    label.textContent = source.kind;
    row.appendChild(label);

    const link = document.createElement("a");
    link.className = "besa-api-source-link";
    link.href = source.href;
    link.textContent = `${source.file}:${source.line}`;
    row.appendChild(link);

    return row;
  }

  function addFunctionMetadata(signature) {
    const declaration = signature.closest("dl.cpp.function, dl.cpp.function-template, dl.c.function");
    if (!declaration || declaration.dataset.besaMetadata === "true") return;
    declaration.dataset.besaMetadata = "true";

    const generated = functionMetadataFor(signature);
    const properties = propertyRow(
      mergedQualifiers(qualifiersFor(signature), generated.qualifiers)
    );
    const source = sourceRow(generated.source);
    if (!properties && !source) return;

    const metadata = document.createElement("div");
    metadata.className = "besa-api-function-metadata";
    if (properties) metadata.appendChild(properties);
    if (source) metadata.appendChild(source);

    let description = declaration.querySelector(":scope > dd");
    if (!description) {
      description = document.createElement("dd");
      declaration.appendChild(description);
    }
    description.prepend(metadata);
  }


  function addEntityMetadata(signature) {
    const declaration = signature.closest("dl.cpp, dl.c");
    if (!declaration || declaration.dataset.besaSourceMetadata === "true") return;

    const source = sourceRow(entitySourceLocation());
    declaration.dataset.besaSourceMetadata = "true";
    if (!source) return;

    const metadata = document.createElement("div");
    metadata.className = "besa-api-function-metadata besa-api-entity-metadata";
    metadata.appendChild(source);

    let description = declaration.querySelector(":scope > dd");
    if (!description) {
      description = document.createElement("dd");
      declaration.appendChild(description);
    }
    description.prepend(metadata);
  }

  function headingText(heading) {
    if (!heading) return "";
    const copy = heading.cloneNode(true);
    for (const permalink of copy.querySelectorAll(".headerlink")) permalink.remove();
    return normalizedText(copy);
  }

  function highlightProgramListingTarget({ scroll = false } = {}) {
    for (const previous of document.querySelectorAll(".besa-api-source-line-target")) {
      previous.classList.remove("besa-api-source-line-target");
    }

    if (!/^#L\d+$/.test(window.location.hash)) return;
    const target = document.getElementById(window.location.hash.slice(1));
    if (!target) return;
    target.classList.add("besa-api-source-line-target");
    if (scroll) {
      window.requestAnimationFrame(() => target.scrollIntoView({ block: "center" }));
    }
  }

  function initializeProgramListingAnchors() {
    const renderedLineNumbers = Array.from(
      document.querySelectorAll("span.linenos, .linenos span")
    ).filter((lineNumber) => /^\d+$/.test((lineNumber.textContent || "").trim()));

    const listingMaps = window.BESA_API_PROGRAM_LISTING_LINES || {};
    const sourceLines = listingMaps[currentDocumentName()];
    const hasExactSourceMap =
      Array.isArray(sourceLines) && sourceLines.length === renderedLineNumbers.length;

    for (const [index, lineNumber] of renderedLineNumbers.entries()) {
      const renderedValue = (lineNumber.textContent || "").trim();
      const mappedValue = hasExactSourceMap ? sourceLines[index] : null;
      const value = Number.isInteger(mappedValue) && mappedValue > 0
        ? String(mappedValue)
        : renderedValue;

      const anchor = document.createElement("a");
      anchor.className = "besa-api-source-line-number";
      anchor.id = `L${value}`;
      anchor.href = `#L${value}`;
      anchor.textContent = value;
      anchor.setAttribute("aria-label", `Link to source line ${value}`);
      lineNumber.replaceChildren(anchor);
    }

    highlightProgramListingTarget({ scroll: true });
    window.addEventListener("hashchange", () => highlightProgramListingTarget());
  }

  function initializeApiOutline() {
    for (const button of document.querySelectorAll(".besa-api-outline-toggle")) {
      const targetId = button.getAttribute("aria-controls");
      const target = targetId ? document.getElementById(targetId) : null;
      if (!target) continue;

      const namespace = button.dataset.besaApiOutlineName || "namespace";
      const setExpanded = (expanded) => {
        button.setAttribute("aria-expanded", expanded ? "true" : "false");
        button.setAttribute(
          "aria-label",
          `${expanded ? "Collapse" : "Expand"} ${namespace}`
        );
        target.hidden = !expanded;
      };

      setExpanded(button.getAttribute("aria-expanded") === "true");
      button.addEventListener("click", () => {
        setExpanded(button.getAttribute("aria-expanded") !== "true");
      });
    }
  }

  function initialize() {
    for (const signature of document.querySelectorAll("dl.cpp.function > dt.sig, dl.cpp.function-template > dt.sig, dl.c.function > dt.sig")) {
      addFunctionMetadata(signature);
    }

    // Entity metadata is page-level: use the first non-function C/C++ declaration on the page.
    // This deliberately does not enumerate entity kinds, so concepts, enums, typedef/using aliases,
    // variables, macros, and future Breathe/Sphinx entity kinds are picked up automatically.
    const entitySignature = document.querySelector(
      "dl.cpp:not(.function):not(.function-template) > dt.sig, dl.c:not(.function) > dt.sig"
    );
    if (entitySignature) addEntityMetadata(entitySignature);
    initializeApiOutline();
    initializeProgramListingAnchors();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
})();
