<!-- SPDX-FileCopyrightText: 2026 BESA developers -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# CLI reference

## `besa cpp generate`

```text
besa cpp generate --path PATH --name NAME [--directory DIRECTORY] [--license SPDX-ID] [--license-text PATH] [--nvim-ycm]
```

Creates `PATH/DIRECTORY` from `share/besa/cpp/vorlage`, substitutes `NAME` as the project name, and
installs the current BESA CMake module into `PATH/DIRECTORY/cmake/besa`.

`--directory` controls only the directory created below `--path`; it is independent of the project
name and defaults to `main`. For example:

```console
besa cpp generate --path ~/software/dice --name dice
```

creates `~/software/dice/main`, while:

```console
besa cpp generate --path ~/software/dice --name dice --directory code
```

creates `~/software/dice/code`. `DIRECTORY` must be a single relative path component.

`--license` supplies the SPDX license identifier written into generated project files. It defaults to
`Apache-2.0`. Generated C++ projects are REUSE-ready: project-owned files receive per-file
`SPDX-FileCopyrightText` and `SPDX-License-Identifier` metadata, files that cannot carry comments use
adjacent `.license` sidecars, and canonical license texts are installed below `LICENSES/`. Vendored
`cmake/besa` files keep BESA's Apache-2.0 attribution rather than being reassigned to the generated
project.

BESA bundles the canonical `Apache-2.0` text used by the default template. When another SPDX
identifier is selected, `--license-text PATH` supplies the corresponding canonical text that is
copied to `LICENSES/<SPDX-ID>.txt`. Generation fails instead of silently producing an incomplete
REUSE tree if that text is unavailable.

`--nvim-ycm` installs local `.nvimrc` and `.ycm_extra_conf.py` files in the generated checkout. Both
files are added to `.gitignore`, since they are developer-local editor configuration rather than
project source. The Neovim configuration inserts SPDX headers and `#ifndef`/`#define` header guards
for new headers.

The YCM configuration always starts with a small language baseline: C++26 for C++-family files and
C17 for C files. If a Spack environment with an active view is present, YCM resolves that view with
`spack location -v` and adds its `include/` directory as a global `-isystem` path. This makes headers
from development dependencies available even when the edited file has no compilation-database entry.

For a source file present in `compile_commands.json`, YCM then appends that source's normalised
compilation flags. For a header in a conventional BESA include tree, YCM first maps the header to the
implementation source that would correspond to it and uses that source's compilation entry. For
example:

```text
src/cpp/include/dice/dice.hpp  -> src/cpp/lib/dice/dice.cpp
src/cuda/include/dice/dice.hpp -> src/cuda/lib/dice/dice.cu
```

The same `include` -> `lib` rule works for nested conventional trees such as test-support libraries.
If neither the file nor its source analogue has a compilation entry, YCM falls back to the baseline
flags plus discovered source/test/generated include directories. It does not merge unrelated
compilation commands into a global include set.

`NAME` currently matches `[a-z][a-z0-9_]*`.

## `besa cpp update`

```text
besa cpp update --project PROJECT [--module-path cmake/besa]
```

Copies the current BESA CMake module into the relative module path. Existing directories are replaced
only when they contain BESA's management marker.

## `besa python generate`

```text
besa python generate
```

Generates the Python template in the current directory. The directory basename becomes the project
and package name. Existing paths which would be overwritten cause an error.

Running `besa`, `besa cpp`, or `besa python` without a leaf command prints the corresponding help and
returns success.
