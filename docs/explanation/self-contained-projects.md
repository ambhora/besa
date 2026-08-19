# Why generated C++ projects vendor BESA

The Python package is a development tool, not a runtime requirement of generated C++ software.
`besa cpp generate` copies the current CMake implementation into `cmake/besa`, and the generated
project finds that local package explicitly.

This has two useful consequences. First, a source checkout remains buildable on a machine which has
CMake and the project's actual dependencies but no Python BESA installation. Second, upgrading the
build abstraction is explicit: `besa cpp update` replaces only the BESA-managed module directory and
never rewrites project-owned CMake.

The generated project's installed CMake package also does not depend on BESA. Target instrumentation
is build-interface-only and BESA emits normal consumer dependency discovery directly into the
project's own `<project>Config.cmake`.
