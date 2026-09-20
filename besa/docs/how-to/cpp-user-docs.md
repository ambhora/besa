<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Build C++ user documentation

Generated C++ projects use two independent documentation tools:

```text
ProperDocs        -> non-versioned project website
cpdoc             -> standalone, versioned API reference
properdocs-cpdoc  -> mounts cpdoc output into the ProperDocs site
```

The checked-in configuration is correspondingly small:

```text
properdocs.yml
cpdoc.yml
docs/
└── ...                    # project documentation in Markdown
api-docs/
└── index.md               # hand-authored API landing-page prose
```

There is no Doxyfile, Sphinx configuration, local ProperDocs hook, or second ProperDocs
configuration. API entity pages are generated directly from cpdoc's semantic API graph.

## Build the site

Enable the generated project's `user-docs` feature, configure it, and build the normal site target:

```bash
cmake -S . -B build -DPROJECT_FEATURES=user-docs
cmake --build build --target user.docs
```

`user.docs` runs ProperDocs. The installed `properdocs-cpdoc` plugin reads `cpdoc.yml`, builds the
selected API versions, and publishes them below `reference/api/`. ProperDocs remains the site root.

For API-only development, use:

```bash
cmake --build build --target user.docs.api
cmake --build build --target user.docs.api.versions
```

The first target renders the current checkout. The second renders the version set selected by
`cpdoc.yml`.

## Configure cpdoc

`cpdoc.yml` is the only API-generator configuration. It identifies the BESA project provider, the
human-authored API introduction, output/work directories, the project-documentation link root, and
version/variant selection. The same configuration can be used without CMake:

```bash
cpdoc --config cpdoc.yml build
cpdoc --config cpdoc.yml versions
```

The version selector supports `all`, `latest:N`, `range:...`, and `refs:...`; `main` remains the
development API. CMake can additionally restrict extraction with `BESA_API_VARIANTS`.

## Link between the two sites

API Markdown and extracted API prose can use semantic `projectdocs:` URLs rather than deployment
hostnames:

```markdown
See the [testing guide](projectdocs:reference/testing/).
```

Source comments may use the equivalent convenience spelling:

```cpp
/**
 * See @projectdocs.
 * See @projectdocs{reference/testing/}.
 */
```

The standalone API renderer resolves these links against the non-versioned ProperDocs root.

In the opposite direction, ProperDocs prose can reference an API symbol with:

```text
@apidocs::myproject::meta::build
```

`properdocs-cpdoc` resolves that symbol to the configured API version and reports unresolved symbol
references instead of emitting silent broken links.

## Author and preview

Project prose remains ordinary ProperDocs Markdown, so it can be previewed with:

```bash
properdocs serve
```

With the cpdoc plugin installed, the API subtree is generated and mounted as part of the same serve
workflow. `api-docs/index.md` is normal Markdown and may contain `projectdocs:` links.

## Install built documentation

After building `user.docs`, a normal CMake install includes the complete site:

```bash
cmake --install build --prefix <prefix>
```

The install source is optional, so installing a build that never generated documentation still
succeeds.
