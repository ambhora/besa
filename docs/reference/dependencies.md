# Dependency reference

`besa_dependency_add()` describes a dependency in two independent dimensions: why the dependency
exists and how it is discovered.

```cmake
besa_dependency_add(
  NAME name
  [VERSION version]
  [KIND NORMAL|BUILD|DEV]
  [PROVIDER CMAKE|PKGCONFIG]
  [VISIBILITY PUBLIC|PRIVATE|INTERFACE]
  [COMPONENTS component...]
  [WHEN selector...]
)
```

## `KIND`

`NORMAL` is the default. A normal dependency belongs to the product dependency graph and is emitted
into the generated `<project>Config.cmake` so consumers resolve it before importing project targets.

`BUILD` describes software needed to construct the project, such as a generator. It is resolved for
the current build but is not emitted into consumer package metadata.

`DEV` describes testing, documentation, QA, analysis, or other developer-only dependencies. It is
not emitted into consumer package metadata.

BESA currently takes a conservative package-export approach and records every selected `NORMAL`
dependency in the consumer config. `VISIBILITY` is retained as project dependency metadata and as a
future link-graph dimension; it does not suppress a normal dependency from package metadata.

## `PROVIDER CMAKE`

This is the default. BESA calls `find_package()` with the requested name/version/components. It does
not force a particular package metadata format. A package can therefore be resolved through normal
CMake discovery, a package configuration, or newer formats supported by the active CMake version.

## `PROVIDER PKGCONFIG`

BESA resolves `PkgConfig`, then creates the conventional imported target with
`pkg_check_modules(... IMPORTED_TARGET ...)`. Normal pkg-config dependencies are reproduced in the
generated consumer configuration.

## Conditional dependencies

All selectors are accepted through `WHEN`:

```cmake
besa_dependency_add(
  NAME Doxygen
  KIND DEV
  PROVIDER CMAKE
  WHEN ALL_OF user-docs
)
```

A dependency whose selector does not match is neither discovered nor written to package metadata.
