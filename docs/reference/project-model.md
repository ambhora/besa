<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Project model

`besa.toml` is the authoritative, build-system-neutral declaration of a BESA C++ project. It says
what the project *can* contain. A backend supplies the requested configuration, BESA resolves it
against the model, and the backend realizes the resulting targets and build actions.

The generated `CMakeLists.txt` is therefore a CMake backend bootstrap rather than a second project
description. In particular, project identity, features, test modes, API profiles, dependencies,
source roots, and conditional directories are not duplicated there.

Every selectable project capability is a feature. `kind` is metadata used for presentation and
analysis; it does not create separate feature namespaces:

```toml
schema = 1

[project]
name = "example"
version = "0.1.0"

[features.build-source]
default = true
kind = "build"

[features.toolchain-cpp]
default = true
kind = "toolchain"

[features.user-docs]
default = false
kind = "documentation"
```

Conditions are structural and may nest `all`, `any`, and `not`:

```toml
when = { all = ["project-foo", { any = ["toolchain-cuda", "toolchain-hip"] }] }
```

API profiles describe compilation contexts independently of ordinary project-feature selection:

```toml
[api.profiles.cpu]
features = ["build-source", "toolchain-cpp"]

[api.profiles.cuda]
features = ["build-source", "toolchain-cpp", "toolchain-cuda"]
predefined = ["__CUDACC__=1"]
```

Dependencies retain BESA's existing dependency semantics without trying to unify them with an
external package manager:

```toml
[[dependencies]]
name = "Catch2"
version = "3"
kind = "dev"
provider = "cmake"
when = { all = ["build-testing"] }
```

Public source roots and conditional project directories are also declared in the model:

```toml
[[sources]]
name = "cpp"
path = "src/cpp"
language = "CXX"
api = "public"
when = { all = ["build-source", "toolchain-cpp"] }

[[directories]]
name = "showcase-hello"
path = "showcases/hello"
api = "none"
when = { all = ["showcase-hello"] }
```

BESA owns the source-prefix conventions below a registered source root. The backend discovers the
appropriate contents instead of requiring an exhaustive source-file list in TOML.

## Portable feature constraints

Feature logic which cannot be represented by a structural condition can be implemented by a small
Python callback. The declaration names the complete feature domain observed by the callback:

```toml
[[constraints]]
name = "accelerator-mode"
features = ["toolchain-cuda", "toolchain-hip"]
callback = "tools/constraints.py:accelerator_mode"
```

The callback receives a dictionary and returns either a boolean or a result dictionary containing
`success`, boolean `result`, and optional `reason`. BESA evaluates only the callback's declared
finite feature domain and caches the truth table. The cache fingerprint includes the declaration and
callback implementation, so changing the function invalidates its cache independently.

## Derived configuration space

For API discovery, BESA finds the features actually referenced by public registrations and closes
that set over any overlapping constraint domains. It varies only that reduced feature space and
crosses it with the declared API profiles. Unrelated features therefore do not cause a global
power-set expansion.

The normalized model and derived API configuration space are generated under the workspace's
`configure_cache/` directory for diagnostics and downstream tooling. They are derived artifacts;
`besa.toml` remains the source of truth.

## Workspace

A BESA workspace contains backend build state, generated code, documentation products, and reusable
configuration analysis as siblings:

```text
<workspace>/
├── build/
├── codegen/
├── docs/
└── configure_cache/
```

`BESA_WORKSPACE` selects the workspace root for the CMake backend. When it is not supplied, BESA uses
the parent of `PROJECT_BINARY_DIR`.

Portable generators write one prefix below `codegen/`. A generated prefix contains `bin/`,
`include/`, `lib/`, and optionally `mod/`; BESA consumes those directories using the same
conventions as ordinary project inputs. Generator context values may be marked as paths, in which
case the contents reachable through the path participate in cache invalidation.
