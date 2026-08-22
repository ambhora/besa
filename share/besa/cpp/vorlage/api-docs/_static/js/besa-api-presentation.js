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

  function addQualifierBadges(signature) {
    const declaration = signature.closest("dl.cpp.function, dl.cpp.function-template");
    if (!declaration || declaration.dataset.besaQualifiers === "true") return;

    const qualifiers = qualifiersFor(signature);
    declaration.dataset.besaQualifiers = "true";
    if (!qualifiers.length) return;

    const row = document.createElement("div");
    row.className = "besa-api-qualifiers";
    row.setAttribute("aria-label", "Function qualifiers");

    for (const qualifier of qualifiers) {
      const badge = document.createElement("span");
      badge.className = "besa-api-qualifier";
      badge.textContent = qualifier;
      row.appendChild(badge);
    }

    declaration.before(row);
  }

  function initialize() {
    for (const signature of document.querySelectorAll("dl.cpp.function > dt.sig, dl.cpp.function-template > dt.sig")) {
      addQualifierBadges(signature);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
})();
