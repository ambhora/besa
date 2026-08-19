# Update the vendored BESA CMake module

A generated C++ project contains a project-owned copy of BESA under `cmake/besa`. Update only that
copy with:

```console
besa cpp update --project .
```

To use another relative location:

```console
besa cpp update --project . --module-path bs/besa
```

`--module-path` is always relative to the project root. BESA refuses absolute paths and paths which
escape the project with `..`.

Updates replace the BESA-owned directory as a unit. BESA checks for its management marker before
replacing an existing directory, so a mistyped module path cannot silently delete an unrelated
project directory. The command never parses or edits project-owned `CMakeLists.txt` files.
