# CLI reference

## `besa cpp generate`

```text
besa cpp generate --path PATH --name NAME [--license SPDX-ID]
```

Creates `PATH/NAME` from `share/besa/cpp/vorlage`, substitutes the project name, and installs the
current BESA CMake module into `PATH/NAME/cmake/besa`.

When `--license` is omitted in an interactive terminal, BESA asks for the SPDX license identifier and
defaults to `Apache-2.0` when the prompt is left empty. In a non-interactive invocation, the omitted
option defaults directly to `Apache-2.0`. BESA accepts the supplied identifier verbatim rather than
maintaining its own SPDX identifier list.

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
