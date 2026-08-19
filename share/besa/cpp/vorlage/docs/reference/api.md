# API reference

The C/C++ API is extracted with Doxygen, rendered through Breathe and Sphinx, and built for the Git
branch heads and tags selected by sphinx-multiversion.

The complete `user.docs` build publishes each available API version below this page. The list is
loaded from the `versions.json` generated alongside the multiversion API tree.

<div id="besa-api-versions">
  <p><a href="main/">Development API (`main`)</a></p>
</div>
<script>
(() => {
  const container = document.getElementById("besa-api-versions");
  fetch("versions.json")
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then((metadata) => {
      const list = document.createElement("ul");
      for (const version of metadata.versions || []) {
        const item = document.createElement("li");
        const link = document.createElement("a");
        link.href = version.url;
        link.textContent = version.name === metadata.default
          ? `${version.name} (default)`
          : version.name;
        item.appendChild(link);
        list.appendChild(item);
      }
      if (list.children.length) container.replaceChildren(list);
    })
    .catch(() => {
      // Keep the static main-branch fallback above when serving only ProperDocs locally or when the
      // multiversion API tree has not been assembled yet.
    });
})();
</script>
