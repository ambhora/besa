# The besa command line

The `besa` Python package is a thin distribution channel for the CMake
modules. It contains no build logic; its job is to put
`share/besa/cmake/` where you want it.

```bash
pip install besa
# or
uv tool install besa
```

Requires Python 3.11 or newer. The package has no runtime dependencies.

## `besa vendor`

```text
besa vendor [DIRECTORY]
```

Copies the installed BESA CMake payload into `DIRECTORY/cmake/besa/`
(default: the current directory) and prints the destination path.

The copy is **atomic and complete**:

1. The payload is copied into a temporary directory next to the
   destination (`cmake/.besa-XXXX/`).
2. An existing `cmake/besa/` is moved aside to `cmake/.besa-backup/`.
3. The new tree is moved into place; the backup is removed.
4. On any failure the backup is restored and the temporary tree deleted.

Because the whole directory is replaced, files that a newer BESA no longer
ships disappear instead of lingering. Re-run after upgrading the package:

```bash
pip install --upgrade besa && besa vendor
git add cmake/besa && git commit -m "Update vendored BESA"
```

Point CMake at the vendored tree with `besa_DIR`:

```cmake
set(besa_DIR "${CMAKE_CURRENT_SOURCE_DIR}/cmake/besa")
find_package(besa CONFIG REQUIRED)
```

!!! note
    The vendored tree is the module source as shipped in the wheel. It
    contains `besaConfig.cmake` but not `besaConfigVersion.cmake`, which
    only the CMake build of BESA generates. Do not pass a version to
    `find_package()` for a vendored copy.

Exit status is `0` on success. If the installed package does not contain the
CMake payload (for example in an unusual installation layout), the command
fails with `BESA CMake data not found at <path>`.

## Python API

The same operation is available programmatically:

```python
from pathlib import Path
from besa.vendor import vendor, VendorError

destination = vendor(Path("myproject"))          # -> myproject/cmake/besa
destination = vendor(Path("myproject"), source=Path("/opt/besa/share/besa/cmake"))
```

`besa.vendor.cmake_share()` returns the payload location inside the current
Python environment, and `besa.__version__` the package version.
