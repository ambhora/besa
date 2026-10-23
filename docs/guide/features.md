# Features

A **feature** is an optional capability of the project: `mpi`, `gpu`,
`openmp`, `tracing`. Features are declared once, selected by the user through
a cache variable, validated at configure time, and then used to select
source units, tests and dependencies.

Features describe *what the project can do*. They are independent of
*which language implements it*: a `gpu` feature may select a CUDA unit, a
HIP unit, or a plain C++ unit, and the manifest keeps the two notions apart.

## Declaring features

```cmake
set(PROJECT_FEATURE "none" CACHE STRING "Selected project features")
besa_set_feature_variable(PROJECT_FEATURE)

besa_add_feature(mpi)
besa_add_feature(gpu)
besa_add_feature(tracing)
```

`besa_add_feature(<name>)` declares one atomic feature. Names may contain
letters, digits, `.`, `_`, `+` and `-`. Each declaration also creates a
feature space of the same name containing exactly that feature, which is
what makes `CONDITION gpu` work later without further ceremony.

`besa_set_feature_variable(<var>)` tells BESA which cache variable carries
the user's selection. Any name works; `PROJECT_FEATURE` is the convention.
Users select features as a CMake list:

```bash
cmake -B build -DPROJECT_FEATURE="mpi;gpu"
cmake -B build -DPROJECT_FEATURE=none       # explicitly nothing
```

## Constraining combinations

By default every combination of declared features is valid. Two mechanisms
narrow that down.

### Pairwise conflicts

```cmake
besa_features_conflict(mpi gpu)
```

The simplest rule: these two may not be enabled together. Any number of
pairs may be declared; selecting a conflicting pair fails with
`selected features 'gpu;mpi' contain a declared conflict`.

### A project feature space

For anything richer than pairwise exclusion, describe the valid
configurations as a [feature space](feature-spaces.md) and make it the
project's:

```cmake
besa_add_feature(host)
besa_add_feature(gpu)
besa_add_feature(mpi)

besa_keyso_one_of(backend host gpu)        # exactly one of host, gpu
besa_keyso_zero_or_one(parallel mpi)       # optionally mpi
besa_keyso_create_feature_space(supported PRODUCT backend parallel)
# supported = { {host}, {gpu}, {host,mpi}, {gpu,mpi} }

besa_set_feature_space(supported DEFAULT host)
```

`besa_set_feature_space(<space> [DEFAULT <singleton-space>])` makes the
selection valid only if it is *exactly* a member of the space. `{}` is
rejected here because the backend must be chosen; `{host, gpu}` is rejected
because only one backend is allowed; `{host, mpi}` is accepted.

`DEFAULT` names a space with exactly one member, used when the user selects
nothing. Every declared feature is such a space, so `DEFAULT host` is the
usual spelling. Without `DEFAULT`, the empty set is used if the space
contains it, and otherwise the first member.

Conflicts and the project space are both enforced. Use whichever reads
better; use both if a space is easier to write without a particular pair
and a conflict removes it afterwards.

## Using features

Once finalized, features drive three kinds of selection, all through a
`CONDITION` argument that names a feature space:

```cmake
# Source units
besa_add_directory(LIBRARY libcore ROOT host   TYPE cpp  CONDITION host)
besa_add_directory(LIBRARY libcore ROOT device TYPE cuda CONDITION gpu)

# Tests
besa_test_add_directory(NAME gpu-tests PREFIX gpu CONDITION gpu TARGET_LIST core::libcore)

# Dependencies recorded for downstream find_dependency()
besa_dependency_add(NAME MPI COMPONENTS CXX CONDITION mpi)
```

Conditions use **subset matching**: a space matches when *any* of its member
sets is contained in the enabled features. `CONDITION gpu` is true for
`{gpu}` and for `{gpu, mpi}`. This is the opposite of the *exact* matching
`besa_set_feature_space()` uses to validate the whole selection — see
[Two interpretations of a space](feature-spaces.md#two-interpretations-of-a-space)
for why both exist.

For logic that `CONDITION` cannot express, the resolved booleans are
available in `if()`:

```cmake
if(PROJECT_FEATURE_GPU AND NOT PROJECT_FEATURE_MPI)
  target_compile_definitions(libcore PRIVATE CORE_SINGLE_DEVICE)
endif()
```

`PROJECT_FEATURE_<NAME>` is published for every declared feature, with the
name upper-cased and punctuation turned into `_`. `BESA_ENABLED_FEATURES`
holds the sorted list.

## What goes into the manifest

The manifest records the declared features, the feature variable, the
explicit project space (by name) and all conflict pairs, together with the
set that was enabled for this configure run:

```json
"features": ["gpu"],
"feature_configuration": {
  "variable": "PROJECT_FEATURE",
  "available": ["host", "gpu", "mpi"],
  "explicit_space": "supported",
  "conflicts": []
}
```

When cpdocs asks for them (`-DBESA_CPDOCS_FEATURE_SETS_OUTPUT=<file>`), BESA
additionally enumerates every valid concrete feature set — the members of
the project space, minus any that hit a conflict — so documentation can be
built per configuration without guessing. Without a project space the full
Cartesian product of declared features is enumerated for that file only;
ordinary configure runs never expand it.

## Guidelines

- **Name capabilities, not implementations.** `gpu`, not `cuda`; `parallel`
  or `mpi`, not `openmpi`. The language belongs to the unit's `TYPE`.
- **Prefer a project space when there is a required choice.** "Pick one
  backend" is a space; it cannot be expressed as conflicts alone because
  conflicts cannot forbid the empty selection.
- **Keep `none` as the default where nothing is required.** It documents
  that the default build is the plain one.
