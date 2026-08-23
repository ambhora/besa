<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Reference

Reference material for vorlage.

For example, build provenance is exposed by @apidocs::vorlage::meta::build.

## Versioned API

The C/C++ API is extracted with Doxygen, rendered through Breathe and Sphinx, and built for `main`
plus the historical Git refs selected by BESA.

The complete `user.docs` build publishes each available API version below this section. Every Sphinx
API page also exposes a version selector. Selecting another version keeps the current page when that
page exists in the target version and otherwise opens that version's API root.

<div id="besa-api-versions">
  <p><a href="api/main/">Open development API (`main`) →</a></p>
</div>
<script>
(() => {
  const container = document.getElementById("besa-api-versions");
  const apiRoot = new URL("api/", window.location.href);
  fetch(new URL("versions.json", apiRoot))
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then((metadata) => {
      const list = document.createElement("ul");
      for (const version of metadata.versions || []) {
        const item = document.createElement("li");
        const link = document.createElement("a");
        link.href = new URL(version.url, apiRoot).href;
        link.textContent = version.name === metadata.default
          ? `${version.name} (default)`
          : version.name;
        item.appendChild(link);
        list.appendChild(item);
      }
      if (list.children.length) container.replaceChildren(list);
    })
    .catch(() => {
      // Keep the static main-branch fallback when the versioned API has not been assembled yet.
    });
})();
</script>
