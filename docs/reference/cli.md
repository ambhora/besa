# CLI reference

## `besa cpp generate`

```text
besa cpp generate --path PATH --name NAME [--directory DIRECTORY] [--license SPDX-ID]
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
