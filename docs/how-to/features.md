<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Configure features

Declare project features and defaults in `besa.toml`:

```toml
[features.build-source]
default = true
kind = "build"

[features.toolchain-cpp]
default = true
kind = "toolchain"

[features.toolchain-cuda]
default = false
kind = "toolchain"

[features.user-docs]
default = false
kind = "documentation"
```

Every selectable project capability is a feature. `kind` is metadata; selection still uses one
feature namespace.

The CMake backend receives feature overrides through `PROJECT_FEATURES`:

```console
cmake -S . -B workspace/build \
  -DPROJECT_FEATURES='toolchain-cuda;~toolchain-cpp'
```

Positive entries enable a feature. `~feature` disables a default feature. Each underlying feature may
appear at most once; contradictory or repeated entries are rejected.

Features with `kind = "toolchain"` are compilation-context features. BESA's CMake backend maps the
reserved `toolchain-*` names it supports to CMake languages and enables those languages only after
the complete feature configuration has been resolved. Toolchain-specific compiler options and
architecture choices remain toolchain/backend configuration rather than fields in `besa.toml`.
