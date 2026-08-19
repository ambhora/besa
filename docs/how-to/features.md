# Configure features

Declare every supported feature before the configuration phase closes:

```cmake
besa_features_add(
  FEATURES
    build-source
    toolchain-cpp
    toolchain-cuda
    toolchain-hip
    toolchain-asm
    user-docs
)

besa_features_default(
  FEATURES
    build-source
    toolchain-cpp
)

besa_configure_complete()
```

`PROJECT_FEATURES` is an override set applied to the defaults:

```console
cmake -S . -B build/cuda \
  -DPROJECT_FEATURES='toolchain-cuda;~toolchain-cpp'
```

Positive entries enable a feature. `~feature` disables a default feature. Each underlying feature may
appear at most once in `PROJECT_FEATURES`; contradictory or repeated entries are rejected.

Features beginning with `toolchain-` are special. BESA currently maps:

- `toolchain-c` to CMake language `C`;
- `toolchain-cpp` to `CXX`;
- `toolchain-cuda` to `CUDA`;
- `toolchain-hip` to `HIP`;
- `toolchain-fortran` to `Fortran`;
- `toolchain-asm` to `ASM`.

BESA enables `ASM` after all other selected toolchain languages. This follows CMake's recommendation
that assembly support be enabled last so an enabled C or C++ compiler can be considered for assembly
sources.

A project may declare another `toolchain-*` name, but enabling it is an error until the installed BESA
version knows how to map it to a CMake language.
