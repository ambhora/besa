<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Contributing

This page provides the minimal contribution conventions for this project. Projects are expected to
extend these instructions with their own review, testing, and release requirements.

## Documentation

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

## Software

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

### License Compliance

This project follows the [REUSE Specification](https://reuse.software/spec/) for machine-readable
license and copyright information. Different files may use different licenses, so the SPDX metadata
on each file is authoritative for that file.

When editing existing files, preserve their `SPDX-FileCopyrightText` and `SPDX-License-Identifier`
information unless the licensing of the file is intentionally being changed. New files should carry
appropriate SPDX metadata, and required license texts should be present below `LICENSES/`.

Before submitting licensing-related changes, run `reuse lint` when REUSE tooling is available and
resolve any reported compliance issues.
