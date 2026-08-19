# BESA

BESA is project-development tooling for declarative, self-contained build descriptions. Its current
focus is C++/CMake plus a minimal Python project generator.

```console
uv run besa cpp generate --path /tmp --name example
cd /tmp/example
cmake --workflow --preset gcc --fresh
```

A generated C++ project vendors the BESA CMake implementation under `cmake/besa`; it does not require
BESA to remain installed in order to build.

Run the BESA regression suite with:

```console
uv run --group test pytest --basetemp=build/test
```

Build the ProperDocs site with:

```console
uv run --group docs properdocs build
```

See the full documentation under `docs/` or the GitHub Pages site.
