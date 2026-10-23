# Feature spaces (Keyso)

**Keyso** is BESA's small algebra for describing sets of valid feature
combinations. It lets you write "exactly one backend, optionally MPI,
optionally OpenMP, but never both" as a few declarations, and have the
result checked, enumerated for documentation, and reused as a condition.

If your project only needs pairwise exclusions, `besa_features_conflict()`
is enough and you can skip this page. Keyso earns its keep when a choice is
*required*, when alternatives come in groups, or when you want the set of
supported configurations written down in one place.

## Vocabulary

A **concrete feature set** is an unordered set of enabled features:
`{}` (nothing enabled), `{mpi}`, `{gpu, mpi}`.

A **feature space** is a *set of concrete feature sets* — the configurations
it considers possible: `{ {host}, {gpu} }` has two members; `{ {}, {mpi} }`
has two members, one of them empty. A space with *no* members is different
from a space whose only member is `{}`.

Every space has a name. Names share the feature naming rules (letters,
digits, `.`, `_`, `+`, `-`). Declaring a feature with `besa_add_feature(x)`
also declares the space `x = { {x} }`.

All Keyso commands belong to the open phase: call them after
`besa_add_feature()` and before `besa_finalize_options()`.

## Constructors

Each constructor builds a named space from previously declared features.

| Command | Result | Example |
| --- | --- | --- |
| `besa_keyso_all_of(S a b c)` | One member containing all listed features | `all_of(dgpu mpi gpu)` → `{ {mpi,gpu} }` |
| `besa_keyso_one_of(S a b c)` | One singleton member per feature | `one_of(backend host gpu)` → `{ {host}, {gpu} }` |
| `besa_keyso_zero_or_one(S a b c)` | The empty set plus one singleton per feature | `zero_or_one(par mpi omp)` → `{ {}, {mpi}, {omp} }` |
| `besa_keyso_any_of(S a b c)` | Every non-empty combination | `any_of(trace t p)` → `{ {t}, {p}, {t,p} }` |

Read them as answers to "how many of these may be enabled?": all, exactly
one, at most one, at least one.

## Combining spaces

```cmake
besa_keyso_create_feature_space(<name> UNION|INTERSECTION|SETMINUS|PRODUCT <space>...)
```

Operations act on **whole members**, never on individual features:

| Operation | Meaning |
| --- | --- |
| `UNION` | Every member of every operand |
| `INTERSECTION` | Members present in every operand |
| `SETMINUS` | Members of the first operand not present in any later operand |
| `PRODUCT` | For each way of picking one member from each operand, the union of the picked sets |

`PRODUCT` is the one you will reach for most. It composes independent
choices:

```cmake
besa_keyso_one_of(backend host gpu)             # { {host}, {gpu} }
besa_keyso_zero_or_one(parallel mpi openmp)     # { {}, {mpi}, {openmp} }
besa_keyso_create_feature_space(supported PRODUCT backend parallel)
# supported = { {host}, {host,mpi}, {host,openmp},
#               {gpu},  {gpu,mpi},  {gpu,openmp} }
```

Six configurations, each of them "one backend and at most one parallel
runtime". `{gpu, mpi, openmp}` is not a member, so it is rejected if the
user asks for it. A `PRODUCT` with an operand that has no members produces
no members.

Ordinary set algebra behaves as expected:

```cmake
besa_keyso_one_of(left host gpu)          # { {host}, {gpu} }
besa_keyso_one_of(right gpu mpi)          # { {gpu}, {mpi} }
besa_keyso_create_feature_space(u UNION left right)         # { {host}, {gpu}, {mpi} }
besa_keyso_create_feature_space(i INTERSECTION left right)  # { {gpu} }
besa_keyso_create_feature_space(d SETMINUS left right)      # { {host} }
```

`SETMINUS` is useful to carve a specific combination out of a product:

```cmake
besa_keyso_create_feature_space(candidates PRODUCT backend parallel)
besa_keyso_all_of(unsupported gpu openmp)      # { {gpu,openmp} }
besa_keyso_create_feature_space(supported SETMINUS candidates unsupported)
# supported = candidates without {gpu,openmp}
```

## Two interpretations of a space

The same space means different things depending on who is asking. This is
the one subtlety worth internalizing.

**As a restriction** — `besa_set_feature_space(S)` — the enabled set must be
*exactly* a member of `S`. `backend = { {host}, {gpu} }` permits `{host}` or
`{gpu}` and rejects `{}` and `{host, gpu}`.

**As a condition** — `CONDITION S` on a unit, test or dependency — `S`
matches when *any* member of `S` is a **subset** of the enabled set.
Additional enabled features do not matter. `CONDITION backend` is true for
`{host}`, `{gpu}` and also `{host, gpu, mpi}`.

The subset rule is what you want for conditions: a GPU unit should be built
whenever `gpu` is on, regardless of what else is on. But it has a
consequence: **any space that contains `{}` matches every configuration as a
condition**, because the empty set is a subset of everything. So
`zero_or_one(parallel mpi openmp)` is a good *restriction* ("at most one")
and a good `PRODUCT` operand, but a useless *condition* — it would select
the unit unconditionally. To gate on "some parallel runtime is enabled", use
`any_of` or `one_of` instead:

```cmake
besa_keyso_one_of(parallel_enabled mpi openmp)
besa_test_add_directory(NAME parallel-tests CONDITION parallel_enabled)
```

| Space | As a restriction | As a condition |
| --- | --- | --- |
| `one_of(S a b)` | exactly one of a, b | a or b is enabled |
| `zero_or_one(S a b)` | at most one of a, b | *always true* |
| `any_of(S a b)` | at least one, any mix | a or b is enabled |
| `all_of(S a b)` | a and b, nothing else | a and b are both enabled |

## Setting the project space

```cmake
besa_set_feature_space(<space> [DEFAULT <singleton-space>])
```

Exactly one space may be the project's. The selection must be an exact
member. `DEFAULT` must name a space with one member that is itself a member
of `<space>`; any declared feature qualifies. Without `DEFAULT`, `{}` is
chosen if it is a member, otherwise the first member in sorted order.

## A complete example

```cmake
set(PROJECT_FEATURE "none" CACHE STRING "Selected features")
besa_set_feature_variable(PROJECT_FEATURE)

besa_add_feature(alpha)
besa_add_feature(beta)
besa_add_feature(mpi)
besa_add_feature(gpu)

besa_keyso_one_of(implementation alpha beta)
besa_keyso_zero_or_one(parallel mpi)
besa_keyso_zero_or_one(acceleration gpu)
besa_keyso_create_feature_space(supported PRODUCT implementation parallel acceleration)
besa_set_feature_space(supported DEFAULT alpha)

besa_register_options(GROUP project VARIABLES PROJECT_FEATURE)
besa_finalize_options()
```

| `-DPROJECT_FEATURE=` | Result |
| --- | --- |
| *(unset)* or `none` | `{alpha}` — the default |
| `beta;mpi;gpu` | accepted: one implementation, mpi, gpu |
| `alpha;beta` | rejected: `feature set 'alpha, beta' is not allowed by project feature space 'supported'` |
| `gamma` | rejected: `unknown feature 'gamma'. Declared features are: alpha;beta;mpi;gpu` |

The eight members of `supported` are exactly what BESA enumerates for cpdocs
when documentation is built per configuration.

## Implementation note

Internally a concrete set is a sorted, `|`-joined string of feature names,
with `@` standing for the empty set, and spaces are lists of such strings in
global properties. None of this is public API; use the commands above.
