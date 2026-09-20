<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Create and build a C++ project

This tutorial creates a C++ project, examines the generated build description, and builds it with two
compilers.

## Generate the project

Install BESA in your Python environment and run:

```console
besa cpp generate --path ~/software/example --name example
cd ~/software/example/main
```

The generator creates the default `main` checkout directory, copies the C++ template, substitutes the
project name, writes the declarative `besa.toml` project model, and installs the current BESA CMake
backend under `cmake/besa`. Use `--directory` when a
different checkout-directory name is desired. Add `--nvim-ycm` when local Neovim and YouCompleteMe
configuration should also be provisioned; those two local files are gitignored.

## Build with GCC

```console
cmake --workflow --preset gcc --fresh
```

The default feature set in `besa.toml` contains `build-source` and `toolchain-cpp`. The CMake
bootstrap begins with `LANGUAGES NONE`; `besa_model_realize()` loads the model and BESA resolves those
features before enabling `CXX` and processing the source prefix.

## Build with Clang

```console
cmake --workflow --preset clang --fresh
```

The build description is unchanged. Only the preset selects a different compiler.

## Disable a default feature

Features passed through `PROJECT_FEATURES` are overrides. Prefix a feature with `~` to disable a
default:

```console
cmake -S . -B build/no-source \
  -DPROJECT_FEATURES='~build-source;~toolchain-cpp'
```

A feature may appear only once in the override list. `foo;~foo`, `foo;foo`, and `~foo;~foo` are all
configuration errors.

## Install the project

```console
cmake --install build/gcc --prefix ~/opt/example
```

BESA generates and installs `exampleConfig.cmake`, `exampleConfigVersion.cmake`, and exported targets.
The installed package does not depend on the vendored BESA module.
