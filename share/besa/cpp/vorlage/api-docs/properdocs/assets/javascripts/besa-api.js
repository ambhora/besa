// SPDX-FileCopyrightText: 2026 BESA developers
// SPDX-License-Identifier: Apache-2.0

(() => {
  "use strict";

  const KIND_MARKERS = {
    namespace: "N",
    module: "M",
    package: "P",
    class: "C",
    struct: "S",
    union: "U",
    enum: "E",
    trait: "T",
    protocol: "P",
    function: "F",
    method: "F",
    constructor: "F",
    type_alias: "T",
    variable: "V",
    attribute: "A",
    property: "P",
    constant: "C",
    macro: "M",
    concept: "C",
  };

  function scriptBase() {
    const scripts = Array.from(document.scripts);
    const script = scripts.find((item) => item.src.includes("besa-api.js"));
    return script ? new URL(".", script.src) : new URL(".", window.location.href);
  }

  function versionRoot() {
    // assets/javascripts/ -> assets/ -> the current version site.
    return new URL("../../", scriptBase());
  }

  function apiRoot() {
    const config = window.BESA_API_CONFIG || {};
    // apiRootUrl is resolved from the script location so branch names containing slashes remain
    // deployment-prefix neutral (for example feature/foo/ under GitHub Pages).
    return new URL(config.apiRootUrl || "../../../", scriptBase());
  }

  function addOutlineTitle() {
    const nav = document.querySelector(".md-sidebar--primary .md-nav--primary");
    if (!nav || nav.querySelector(".besa-api-outline-title")) return;
    const title = document.createElement("div");
    title.className = "besa-api-outline-title";
    title.textContent = "Outline";
    nav.prepend(title);
  }

  function addKindMarkers() {
    const config = window.BESA_API_CONFIG || {};
    const configuredKinds = config.entityKinds || {};
    const currentVersionRoot = versionRoot();
    document.querySelectorAll(".md-nav--primary a.md-nav__link").forEach((link) => {
      if (link.querySelector(".besa-api-nav-kind")) return;
      const absolute = new URL(link.href, window.location.href);
      const relative = absolute.href.startsWith(currentVersionRoot.href)
        ? absolute.href.slice(currentVersionRoot.href.length).split(/[?#]/, 1)[0]
        : "";
      let kind = configuredKinds[relative];
      if (!kind) {
        const match = absolute.pathname.match(/\/(namespace|module|package|class|struct|union|enum|trait|protocol|function|method|constructor|type_alias|variable|attribute|property|constant|macro|concept)-[^/]+\/?$/);
        kind = match ? match[1] : "";
      }
      if (!kind) return;
      const marker = document.createElement("span");
      marker.className = "besa-api-nav-kind";
      marker.textContent = KIND_MARKERS[kind] || "·";
      link.prepend(marker);
    });

    document.querySelectorAll(".api-kind[data-kind]").forEach((marker) => {
      marker.textContent = KIND_MARKERS[marker.dataset.kind] || "·";
    });
  }

  function renameToc() {
    const title = document.querySelector(".md-sidebar--secondary .md-nav__title");
    if (title) title.textContent = "On this page";
  }

  async function addHeaderActions() {
    const config = window.BESA_API_CONFIG || {};
    const inner = document.querySelector(".md-header__inner");
    if (!inner || inner.querySelector(".besa-api-header-actions")) return;

    const actions = document.createElement("div");
    actions.className = "besa-api-header-actions";

    const projectDocs = document.createElement("a");
    projectDocs.className = "besa-api-project-docs";
    projectDocs.textContent = "← Project documentation";
    projectDocs.href = new URL(config.projectDocsUrl || "../../../../../", scriptBase()).href;
    actions.append(projectDocs);

    const select = document.createElement("select");
    select.className = "besa-api-version-select";
    select.setAttribute("aria-label", "API version");
    const fallback = document.createElement("option");
    fallback.value = config.version || "main";
    fallback.textContent = config.version || "main";
    select.append(fallback);
    actions.append(select);
    inner.append(actions);

    try {
      const root = apiRoot();
      const response = await fetch(new URL("versions.json", root));
      if (!response.ok) return;
      const metadata = await response.json();
      if (!Array.isArray(metadata.versions)) return;
      select.replaceChildren();
      metadata.versions.forEach((version) => {
        const option = document.createElement("option");
        option.value = version.url || `${version.name}/`;
        option.textContent = version.name;
        option.selected = version.name === config.version;
        select.append(option);
      });
      select.addEventListener("change", () => {
        const currentRoot = versionRoot();
        const relative = window.location.href.startsWith(currentRoot.href)
          ? window.location.href.slice(currentRoot.href.length)
          : "";
        window.location.href = new URL(select.value + relative, root).href;
      });
    } catch (_error) {
      // A standalone single-version preview intentionally has no versions.json.
    }
  }

  function simplifyFooter() {
    const copyright = document.querySelector(".md-footer-copyright");
    if (!copyright || copyright.querySelector(".besa-api-footer-credit")) return;
    copyright.querySelectorAll("a[href*='mkdocs'], a[href*='material']").forEach((node) => node.remove());
    const credit = document.createElement("span");
    credit.className = "besa-api-footer-credit";
    credit.textContent = "Created with ProperDocs.";
    copyright.append(credit);
  }

  function initialize() {
    addOutlineTitle();
    addKindMarkers();
    renameToc();
    addHeaderActions();
    simplifyFooter();
  }

  document.addEventListener("DOMContentLoaded", initialize);
  if (typeof document$ !== "undefined" && document$ && typeof document$.subscribe === "function") {
    document$.subscribe(initialize);
  }
})();
