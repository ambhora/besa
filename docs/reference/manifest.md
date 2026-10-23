# The manifest

At the end of every configure run BESA writes `build/besa/manifest.json`
(path published as `BESA_MANIFEST`). It is the single machine-readable
description of the project as BESA understood it: the units it discovered,
the options it registered, the features it declared, and what was enabled.
Documentation generators, CI matrix builders and packaging scripts can read
it instead of parsing CMake.

The format is versioned by the `besa-manifest` field; this page describes
version **1**.

## Top level

```json
{
  "besa-manifest": 1,
  "project": "greet",
  "features": ["gpu"],
  "feature_configuration": { ... },
  "options": [ ... ],
  "units": [ ... ]
}
```

| Field | Content |
| --- | --- |
| `besa-manifest` | Schema version, currently `1` |
| `project` | `PROJECT_NAME` |
| `features` | Sorted list of features enabled in this configuration |
| `feature_configuration` | How features are declared and constrained (below) |
| `options` | Registered cache variables (below) |
| `units` | Discovered source units (below) |

## `feature_configuration`

```json
{
  "variable": "PROJECT_FEATURE",
  "available": ["host", "gpu", "mpi"],
  "explicit_space": "supported",
  "conflicts": [["gpu", "mpi"]]
}
```

| Field | Content |
| --- | --- |
| `variable` | The cache variable connected with `besa_set_feature_variable()`; `""` if none |
| `available` | Declared features, in declaration order |
| `explicit_space` | Name of the project feature space, or `""` |
| `conflicts` | Pairs from `besa_features_conflict()`, each sorted |

The members of the project space are not expanded here. They are written
to the cpdocs feature-sets file on request (below).

## `options`

One object per variable passed to `besa_register_options()`, in
registration order:

```json
{
  "name": "BUILD_DEVTOOLS",
  "group": "build",
  "type": "STRING",
  "value": "asan;ubsan",
  "description": "Enabled development tools",
  "allowed": []
}
```

| Field | Content |
| --- | --- |
| `name` | Cache variable name |
| `group` | Group given to `besa_register_options()` |
| `type` | Cache entry type (`BOOL`, `STRING`, `PATH`, …) |
| `value` | Value in this configuration |
| `description` | The cache `HELPSTRING` |
| `allowed` | The cache `STRINGS` property, if set |

## `units`

One object per unit attached with `besa_add_directory()` /
`besa_add_subdirectory()`, in declaration order. Units skipped by a
`CONDITION` do not appear.

```json
{
  "id": "src",
  "type": "cpp",
  "language": "cpp",
  "generated": false,
  "source-type": null,
  "headers": ["/abs/src/include"],
  "sources": ["/abs/src/lib"],
  "modules": ["/abs/src/module"],
  "executables": [],
  "api": [{"path": "/abs/src/include"}],
  "parse": {
    "language": "cpp",
    "standard": "c++20",
    "compile-database": "/abs/build/compile_commands.json"
  }
}
```

| Field | Content |
| --- | --- |
| `id` | The unit's root relative to `PROJECT_SOURCE_DIR` |
| `type` | Built-in type after resolution: `c`, `cpp`, `cuda`, `hip`, `fortran`, `bin` |
| `language` | Semantic language presented to users; same as `type` except `null` for `bin` |
| `generated` | `true` for generated units |
| `source-type` | The registered custom type name for generated units, else `null` |
| `headers` | Public header roots (`<root>/include`), present if the directory exists or the unit is generated |
| `sources` | Implementation roots (`<root>/lib`); for `bin`, the individual source files |
| `modules` | `<root>/module` (`cpp`) or `<root>/mod` (`fortran`) when present |
| `executables` | For `bin` units, the source files, one executable each |
| `api` | Objects `{"path": <header-root>[, "generated": true]}` — what a documentation extractor should parse |
| `parse.language` | Parser language: `c`, `cpp` (also for `cuda` and `hip`), `fortran`; absent for `bin` |
| `parse.standard` | `c<N>`, `c++<N>`, `cuda<N>`, `hip<N>` from the matching `CMAKE_<LANG>_STANDARD`, if set |
| `parse.compile-database` | Path of `compile_commands.json` when the generator produced one |

For generated units all roots point into `build/besa/codegen/<unit>/`.

## Related files

### cpdocs feature sets

Written when `BESA_CPDOCS_FEATURE_SETS_OUTPUT` is set:

```json
{
  "cpdocs-feature-sets": 1,
  "generator": "besa",
  "project": {"name": "greet", "version": "1.2.3"},
  "feature-sets": [
    {"features": []},
    {"features": ["gpu"]},
    {"features": ["gpu", "mpi"]}
  ]
}
```

The members of the project feature space (or, without one, every
combination of declared features), minus any that violate a declared
conflict. Sets are unnamed on purpose: each object is exactly what to pass
back to reproduce that configuration.

### cpdocs feature set (input)

Read when `BESA_CPDOCS_FEATURE_SET` is set:

```json
{"cpdocs-feature-set": 1, "features": ["gpu"]}
```

BESA forces the feature variable to this list (or `none` if empty) before
resolving features.

### cpdocs manifest

Written when `BESA_CPDOCS_MANIFEST_OUTPUT` is set. Same `options` and
`units` as the project manifest under a `"cpdocs-manifest": 1` header; the
selected feature set is omitted because cpdocs already knows it.

### Installation manifest

Written at install time to `share/<project>/install-manifest.json`; see
[Installation and packaging](../guide/packaging.md#the-installation-manifest).
