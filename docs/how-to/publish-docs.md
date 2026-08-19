# Build and publish the documentation

The site is a normal ProperDocs project rooted at `properdocs.yml` with source under `docs/`.

Build locally:

```console
uv run --group docs properdocs build
```

Preview while editing:

```console
uv run --group docs properdocs serve
```

The generated static site is written to `site/`.

## GitHub Pages

`.github/workflows/docs.yml` runs on pushes to `main` and on manual dispatch. It:

1. checks out the repository;
2. installs uv and Python;
3. runs the ProperDocs build with the project's docs dependency group;
4. uploads `site/` as a GitHub Pages artifact;
5. deploys that artifact in a separate `github-pages` deployment job.

In the repository settings, select **GitHub Actions** as the Pages build/deployment source. The
workflow needs no generated documentation committed to the repository.
