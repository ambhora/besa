# BESA

BESA provides a small declarative layer for project development. Its C++ support is designed around a
specific boundary: **the project describes intent, while BESA implements recurring CMake mechanics**.
The Python command is used only to generate or update project resources; generated C++ projects vendor
their BESA CMake module and build independently afterwards.

The current command surface is deliberately small:

```console
besa cpp generate --path <project-root> --name <project-name> [--directory main] [--license Apache-2.0]
besa cpp update --project <project-root> [--module-path cmake/besa]
besa python generate
```

For C++, BESA provides feature resolution, `toolchain-*` language activation, selectors, feature
constraints, dependency bookkeeping, conventional source directories, test discovery, release
version generation, package exports, sanitizers, coverage, formatting, clang-tidy, surrogate-header
checks, and Sphinx/Breathe documentation backed by Doxygen XML.

## Documentation structure

The documentation follows the Diátaxis organization:

- **Tutorials** walk through complete first-use workflows.
- **How-to guides** solve specific tasks in an existing project.
- **Reference** specifies commands, functions, variables, and conventions.
- **Explanation** records the design model and the boundaries BESA intentionally maintains.
