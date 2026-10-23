# Installation

BESA ships as a directory of CMake modules. Your project finds it with
`find_package(besa CONFIG REQUIRED)`. There are three ways to make that call
succeed; pick whichever fits your workflow.

## Option 1: Install the CMake package

Build and install BESA like any other CMake project. Nothing is compiled, so
this takes a second.

```bash
git clone https://github.com/ambhora/besa.git
cmake -S besa -B besa/build -DCMAKE_INSTALL_PREFIX="$HOME/.local"
cmake --install besa/build
```

This installs `share/besa/cmake/` below the prefix, where `find_package()`
looks on every platform. Point consumers at the prefix:

```bash
cmake -S myproject -B build -DCMAKE_PREFIX_PATH="$HOME/.local"
```

Two cache variables control the layout, should you need them:

| Variable | Default | Purpose |
| --- | --- | --- |
| `BESA_INSTALL_DATADIR` | `share` | Architecture-independent data, relative to the prefix |
| `BESA_INSTALL_CMAKEDIR` | `share/besa/cmake` | Where `besaConfig.cmake` is installed |

The installed package carries a `besaConfigVersion.cmake`, so
`find_package(besa 0.4 CONFIG REQUIRED)` works and rejects installations that
are too old.

## Option 2: Vendor the modules into your repository

If you would rather not depend on BESA being installed on every machine that
builds your project, copy the modules into the repository. The `besa` Python
package exists for exactly this.

```bash
pip install besa          # or: uv tool install besa
cd myproject
besa vendor               # writes cmake/besa/ and prints the path
```

`besa vendor` replaces `cmake/besa/` atomically: the new payload is staged
next to it and swapped in, so a failed copy never leaves a half-updated tree.
Commit the directory and tell CMake where it is:

```cmake
cmake_minimum_required(VERSION 4.3)
project(myproject VERSION 1.0.0 LANGUAGES NONE)
set(besa_DIR "${CMAKE_CURRENT_SOURCE_DIR}/cmake/besa")
find_package(besa CONFIG REQUIRED)
```

Re-run `besa vendor` after upgrading the Python package to pick up a newer
BESA. Because the devtool and warning catalogs live in BESA rather than in
your project, updating the vendored modules can make new capabilities
available without touching your `CMakeLists.txt`.

!!! note
    The vendored tree does not include `besaConfigVersion.cmake`, which the
    CMake build generates. Omit the version argument from `find_package()`
    when using a vendored copy. See [The besa command line](../reference/cli.md)
    for details.

## Option 3: Use the source checkout directly

For experimenting, the source tree is itself a valid package root:

```bash
cmake -S myproject -B build -Dbesa_DIR=/path/to/besa/share/besa/cmake
```

## Verifying the installation

A minimal project that does nothing but find the package and finalize an
empty configuration:

```cmake
cmake_minimum_required(VERSION 4.3)
project(check VERSION 0.1.0 LANGUAGES NONE)
find_package(besa CONFIG REQUIRED)
besa_finalize_options()
```

Configuring it prints BESA's configuration summary:

```text
-- check configuration:
--   Features          : none
--   Devtools          : none
--   Warning policy    : minimal
--   Test modes        : none
--   Build testing     : OFF
--   Release type      : dev
--   ...
```

## Tool prerequisites

BESA itself needs only CMake 4.3+. Some capabilities call external programs
when — and only when — you select them:

| You select | BESA looks for |
| --- | --- |
| `BUILD_DEVTOOLS=format` | `clang-format` |
| `BUILD_DEVTOOLS=linting` | `clang-tidy`, `run-clang-tidy` |
| `BUILD_DEVTOOLS=coverage` with Clang | `llvm-profdata`, `llvm-cov` |
| `BUILD_DEVTOOLS=coverage` with GCC | `gcovr` |
| `besa_add_cpdocs_docs()` | `cpdocs` |
| `besa_add_user_docs()` | `cpdocs`, `properdocs` |
| `RELEASE_TYPE=dev` (the default) | `git`, optional — falls back to `nogit` |

Sanitizers (`asan`, `lsan`, `ubsan`) need a GCC or Clang toolchain with the
corresponding runtime libraries; no extra programs are required.
