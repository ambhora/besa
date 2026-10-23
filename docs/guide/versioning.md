# Versions and release metadata

Every BESA project gets a generated header, `<project>/version.hpp`, that
exposes the project version, release channel, packaging provenance and
build information as `constexpr` C++. It is attached to every library in the
project and installed with the public headers, so downstream code can ask a
library what it is.

## The release options

Four cache variables describe the release. BESA creates them with defaults
if the project does not; register them with `besa_register_options()` if you
want them in the manifest.

| Variable | Default | Values | Meaning |
| --- | --- | --- | --- |
| `RELEASE_TYPE` | `dev` | `dev`, `alpha`, `beta`, `rc`, `release` | Release channel |
| `RELEASE_REVISION` | `1` | integer | Pre-release revision (`rc.2`) |
| `PKGBUILDER_ID` | `vanilla` | string | Who built the package (a distribution, a site) |
| `PKGBUILDER_REVISION` | `1` | string | The packager's own revision |

`RELEASE_TYPE` and `RELEASE_REVISION` combine with `project(... VERSION ...)`
into a semantic version string, published as `PROJECT_SEMVER`:

| `RELEASE_TYPE` | `PROJECT_SEMVER` for `VERSION 1.2.3` |
| --- | --- |
| `release` | `1.2.3` |
| `rc` (revision 2) | `1.2.3-rc.2` |
| `beta` | `1.2.3-beta.1` |
| `alpha` | `1.2.3-alpha.1` |
| `dev` | `dev.<branch>.<short-hash>`, e.g. `dev.main.3caacb0`; `dev.nogit.nogit` outside a git checkout |

The `dev` form intentionally does not look like a released version, so a
development build can never be mistaken for `1.2.3`. An invalid
`RELEASE_TYPE` fails configuration.

## The generated header

```cpp
#include <greet/version.hpp>

namespace greet::meta {

enum class release_type { development, release, alpha, beta, release_candidate };

struct semantic_version { std::uint32_t major, minor, patch, tweak; };
struct release_info     { release_type type; std::uint32_t revision; };
struct package_info     { std::string_view builder, revision; };
struct build_info       { std::string_view compiler, compiler_version, system, processor, build_type; };

constexpr semantic_version version() noexcept;   // {1, 2, 3, 0}
constexpr release_info     release() noexcept;   // {release_type::development, 1}
constexpr package_info     package() noexcept;   // {"vanilla", "1"}
constexpr build_info       build() noexcept;     // {"GNU", "14.2.0", "Linux", "x86_64", "Debug"}

constexpr std::string_view to_string(semantic_version) noexcept;  // "1.2.3"
constexpr std::string_view to_string(release_type) noexcept;      // "dev", "rc", ...
constexpr std::string_view to_string(release_info) noexcept;      // "dev", "rc.2", "release"
constexpr std::string_view to_string(build_info) noexcept;        // "GNU 14.2.0; Linux/x86_64; Debug"

} // namespace greet::meta
```

The namespace is the project name with non-identifier characters replaced
by `_`. The header requires C++17 (`std::string_view`) and uses only
`<cstdint>` and `<string_view>`.

Typical uses:

```cpp
// --version output
std::cout << greet::meta::to_string(greet::meta::version()) << ' '
          << greet::meta::to_string(greet::meta::release()) << '\n';

// Compile-time guards
static_assert(greet::meta::version().major == 1);

// Diagnostics
log("built with {}", greet::meta::to_string(greet::meta::build()));
```

`build()` describes *this particular build*, not the project version:
compiler and version, `CMAKE_SYSTEM_NAME`, `CMAKE_SYSTEM_PROCESSOR`, and
`CMAKE_BUILD_TYPE` (or `multi-config`). It is meant for diagnostics; the
string format is not stable.

## Where it lives

The header is written during `besa_finalize_options()` to

```text
build/besa/codegen/meta/include/<project>/version.hpp
```

At finalization BESA attaches that include root to **every** BESA library
(as a `PUBLIC`, or `INTERFACE` for header-only libraries, file set) and
installs it to `include/`. There is no special target to link against; any
code that can see the library's headers can include the version header.

## Package version strings

Downstream, `find_package(greet)` sets `greet_VERSION_STRING` to
`PROJECT_SEMVER`, while the generated `greetConfigVersion.cmake` uses
`PROJECT_VERSION` with `SameMajorVersion` compatibility — so version
*requests* work on the numeric version and the full semver is available for
display.

## Reproducible packaging

`PKGBUILDER_ID` and `PKGBUILDER_REVISION` exist so that a distribution or
an HPC site can mark its packages without patching the project:

```bash
cmake -B build -DRELEASE_TYPE=release -DPKGBUILDER_ID=spack -DPKGBUILDER_REVISION=3
```

The values are escaped into string literals, so any text is safe.
