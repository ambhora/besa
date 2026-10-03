# BESA

BESA is a declarative CMake project model. Projects describe **features**, **valid feature spaces**, and
**semantic source units**; BESA lowers that model into CMake targets and a machine-readable manifest.
The same model is consumed by cpdocs, so documentation does not require a second project description.

Features and source languages are independent concepts. A project feature such as `gpu` may select a
CUDA source unit, but the feature is still just a project capability while `cuda` is the unit's language.

```cmake
cmake_minimum_required(VERSION 3.25)
project(example VERSION 1.0.0 LANGUAGES NONE)
find_package(besa CONFIG REQUIRED)

besa_add_feature(mpi)
besa_add_feature(gpu)

besa_keyso_zero_or_one(parallel mpi)
besa_keyso_zero_or_one(acceleration gpu)
besa_keyso_create_feature_space(supported PRODUCT parallel acceleration)
besa_set_feature_space(supported)
besa_configure_complete()

besa_add_subdirectory(DIRECTORY src/core TYPE cpp)
besa_add_subdirectory(DIRECTORY src/gpu TYPE cuda CONDITION gpu)
besa_add_subdirectory(DIRECTORY bin TYPE bin)
```

Built-in semantic types are `c`, `cpp`, `cuda`, `hip`, `fortran`, and `bin`. Their manifest languages
are respectively `c`, `cpp`, `cuda`, `hip`, `fortran`, and no single language for `bin`. C/C++/CUDA/HIP
units use `include/` and `lib/`; Fortran additionally uses `mod/`; `bin` turns top-level `.c`/`.cpp`
files into executables.

Generators register a custom type that resolves to one built-in type:

```cmake
besa_register_subdirectory_type(
  jnum
  FUNCTION jnum_add_subdirectory
  RESOLVES_TO cpp
  GENERATED
)

besa_add_subdirectory(DIRECTORY schema TYPE jnum)
```

BESA owns the generated prefix and the global `codegen` target. The callback receives `SOURCE_DIR`,
`BUILD_DIR`, `OUTPUT_DIR`, and `OUTPUT_TARGET_VARIABLE`; any extra `ARGS` supplied to
`besa_add_subdirectory()` are forwarded unchanged. This lets cpdocs build `codegen` on the host and
then read the generated `include/`, `lib/`, and (for Fortran) `mod/` roots without building the target
application.
