// -------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------
(() => {
  "use strict";

  function targetForVersion(apiRoot, page, version) {
    const root = new URL(version.url, apiRoot);
    if (Array.isArray(version.pages) && version.pages.includes(page)) {
      return new URL(page, root).href;
    }
    return root.href;
  }

  async function initialize(select) {
    const apiRoot = new URL(select.dataset.besaApiRoot, window.location.href);
    const page = select.dataset.besaApiPage;
    const response = await fetch(new URL("versions.json", apiRoot));
    if (!response.ok) {
      return;
    }

    const metadata = await response.json();
    const versions = Array.isArray(metadata.versions) ? metadata.versions : [];
    if (versions.length === 0) {
      return;
    }

    select.replaceChildren();
    for (const version of versions) {
      const option = document.createElement("option");
      option.value = version.name;
      option.textContent = version.name;
      const versionRoot = new URL(version.url, apiRoot);
      if (window.location.href.startsWith(versionRoot.href)) {
        option.selected = true;
      }
      select.append(option);
    }

    select.disabled = false;
    select.addEventListener("change", () => {
      const version = versions.find((item) => item.name === select.value);
      if (version) {
        window.location.assign(targetForVersion(apiRoot, page, version));
      }
    });
  }

  for (const select of document.querySelectorAll(".besa-api-version-select")) {
    initialize(select).catch(() => {
      select.disabled = true;
    });
  }
})();
