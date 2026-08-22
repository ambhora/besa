# CLI reference

## `besa cpp generate`

```text
besa cpp generate --path PATH --name NAME [--directory DIRECTORY] [--license SPDX-ID] [--nvim-ycm]
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
`Apache-2.0`. License selection is entirely command-line driven; BESA never prompts on stdin. BESA
accepts the supplied identifier verbatim rather than maintaining its own SPDX identifier list.

`--nvim-ycm` installs local `.nvimrc` and `.ycm_extra_conf.py` files in the generated checkout. Both
files are added to `.gitignore`, since they are developer-local editor configuration rather than
project source. The Neovim configuration inserts SPDX headers and `#ifndef`/`#define` header guards
for new headers.

The YCM configuration always starts with a small language baseline: C++26 for C++-family files and
C17 for C files. For a source file present in `compile_commands.json`, YCM appends that source's
normalised compilation flags. For a header in a conventional BESA include tree, YCM first maps the
header to the implementation source that would correspond to it and uses that source's compilation
entry. For example:

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
