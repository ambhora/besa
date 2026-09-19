<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# How to contribute

This page provides the minimal contribution conventions for this project. Projects are expected to
extend these instructions with their own review, testing, and release requirements.

## How to contribute to the docs

The prose documentation lives below `docs/`. When `repo_url` is configured in `properdocs.yml`, each
ProperDocs page provides an **Edit this page** action that opens the corresponding source file in the
repository on the branch or tag being viewed. This is the preferred starting point for small
documentation fixes.

For larger changes, edit the Markdown files locally and preview the site with:

```console
properdocs serve
```

The C/C++ API reference is generated from source declarations and documentation comments. Do not
edit generated API pages directly; change the corresponding source or API documentation input
instead.

## How to contribute to the software

The following is intentionally a minimal project policy and can be replaced as the project develops.

Create a focused branch, make the change, run the relevant tests, and submit it through the
repository's normal review workflow. Keep commits understandable and avoid mixing unrelated changes.

### Developer Certificate of Origin

Contributions use the [Developer Certificate of Origin (DCO) 1.1](https://developercertificate.org/).
Every commit must carry a sign-off. The usual way to add it is:

```console
git commit -s
```

The commit message must contain a line of the form:

```text
Signed-off-by: Name <email@example.com>
```

The sign-off certifies the Developer Certificate of Origin 1.1.

### License

Unless a file states otherwise, contributions are made under the project license:
`BESA_PROJECT_LICENSE`. Keep existing SPDX copyright and license identifiers intact when editing
files, and add appropriate SPDX metadata to new files.

If the project uses the AGPL-3.0 API Usage Exception, `excepted.api` is the authoritative list of
files whose interfaces form the Excepted API. The API boundary is deliberately defined by that file
rather than by the size, purpose, or commercial character of software using the API. Changes that
add, remove, or relocate public API files must update `excepted.api` as part of the same contribution.
The complete combined terms are stored in
`LICENSES/LicenseRef-AGPL-3.0-API-Usage-Exception.txt`.
