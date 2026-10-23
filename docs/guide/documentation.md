# Documentation targets

BESA does not generate documentation itself. It does two things that make
documentation generators' lives easier: it **describes the project** in a
manifest that an API documentation tool can consume, and it provides
**build targets** that invoke two such tools with the right inputs:

- [cpdocs](https://github.com/ambhora/cpdocs) — semantic API reference for
  C, C++ (including CUDA and HIP headers) and Fortran, driven directly by
  BESA's manifest;
- [ProperDocs](https://properdocs.org/) — narrative documentation sites
  from Markdown, which can embed the cpdocs output.

Both are optional. Projects that use another documentation stack can read
the [manifest](../reference/manifest.md) themselves.

## What BESA tells cpdocs

cpdocs needs to know which headers form the public API, in which language
they should be parsed, with which compile flags, and which configurations
of the project exist. Rather than a second project description, cpdocs
asks BESA, through three cache variables that a documentation run sets:

| Variable | Direction | Content |
| --- | --- | --- |
| `BESA_CPDOCS_FEATURE_SETS_OUTPUT` | BESA → cpdocs | Every valid concrete feature set, so documentation can be built per configuration |
| `BESA_CPDOCS_FEATURE_SET` | cpdocs → BESA | A JSON file naming the one concrete feature set to configure for this run; it overrides the feature variable |
| `BESA_CPDOCS_MANIFEST_OUTPUT` | BESA → cpdocs | The units and options of this one configuration, with parser hints and the compilation database |

A documentation run therefore looks like: configure once with
`FEATURE_SETS_OUTPUT` to learn the configurations; then, for each
configuration, configure with `FEATURE_SET` and `MANIFEST_OUTPUT`, build the
`besa.cpdocs` target (which runs every code generator so generated headers
exist), and extract. Users never do this by hand — `cpdocs` does — but it
explains why these variables exist.

The per-configuration manifest carries, for each unit:

```json
{
  "id": "src", "type": "cpp", "language": "cpp", "generated": false, "source-type": null,
  "headers": ["/path/to/src/include"], "sources": ["/path/to/src/lib"],
  "modules": [], "executables": [],
  "api": [{"path": "/path/to/src/include"}],
  "parse": {"language": "cpp", "standard": "c++20", "compile-database": "/path/to/build/compile_commands.json"}
}
```

`language` is what documentation presents (`cuda` stays `cuda`); `parse.language`
is what the extractor should use (`cuda` and `hip` headers parse as `cpp`).
`besa_finalize_options()` always enables `CMAKE_EXPORT_COMPILE_COMMANDS` so
the compilation database is available on generators that support it.

Because features and languages are independent in BESA, cpdocs can present
"the API when `gpu` is enabled" without conflating it with "the CUDA API".

## API reference targets

```cmake
besa_add_cpdocs_docs(
  NAME <target>
  CONFIG <cpdocs-config-file>
  [OUTPUT_DIRECTORY <dir>]                 # default: build/besa/docs/api/current
  [VERSIONS_NAME <target>]                 # default: <NAME>.versions
  [VERSIONS_OUTPUT_DIRECTORY <dir>]        # default: build/besa/docs/api/versions
  [INSTALL_DIRECTORY <dir>]                # default: <docdir>/api/current
  [VERSIONS_INSTALL_DIRECTORY <dir>]       # default: <docdir>/api
  [NO_INSTALL]
)
```

Creates two custom targets:

- `<NAME>` runs `cpdocs --config <CONFIG> build --version main` into the
  output directory — the API of the current checkout;
- `<NAME>.versions` runs `cpdocs --config <CONFIG> versions` — the API of
  every released version the cpdocs configuration lists.

Both clear their output directory first and work from
`build/besa/docs/work/cpdocs/`. Unless `NO_INSTALL` is given, the outputs
are installed (optionally — missing output is not an error) under
`CMAKE_INSTALL_DOCDIR`. `CONFIG` is resolved relative to the project source
directory; `cpdocs` must be on `PATH`.

```cmake
besa_add_cpdocs_docs(NAME api CONFIG docs/cpdocs.yml)
```

```bash
cmake --build build --target api            # API of this checkout
cmake --build build --target api.versions   # all documented releases
```

## Narrative documentation targets

```cmake
besa_add_user_docs(
  NAME <target>
  PROPERDOCS_CONFIG <properdocs.yml>
  CPDOCS_CONFIG <cpdocs-config-file>
  [OUTPUT_DIRECTORY <dir>]        # default: build/besa/docs/site
  [INSTALL_DIRECTORY <dir>]       # default: CMAKE_INSTALL_DOCDIR
)
```

Creates the cpdocs targets `<NAME>.api` and `<NAME>.api.versions` (not
installed separately) and a `<NAME>` target that runs
`properdocs build --config-file <PROPERDOCS_CONFIG> --site-dir <OUTPUT_DIRECTORY>`
from the project source directory. The site is installed to
`INSTALL_DIRECTORY`. `properdocs` must be on `PATH`.

```cmake
besa_add_user_docs(NAME docs PROPERDOCS_CONFIG properdocs.yml CPDOCS_CONFIG docs/cpdocs.yml)
```

```bash
cmake --build build --target docs.api docs   # API reference, then the site
```

How the site includes the API reference is up to the ProperDocs
configuration — typically by pointing a nav entry or a plugin at
`build/besa/docs/api/current`.

## Where documentation lives in the build tree

```text
build/besa/docs/
├── api/current/        # besa_add_cpdocs_docs() / <NAME>.api
├── api/versions/       # versioned API
├── site/               # besa_add_user_docs()
└── work/cpdocs/        # cpdocs working directories
```

`BESA_DOCS_DIRECTORY` points at the root; `BESA_WORKSPACE` relocates all of
`build/besa/`.
