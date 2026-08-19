# Configuration families are intentionally orthogonal

BESA keeps several configuration concepts separate because they answer different questions.

A **feature** changes project capability or topology: examples are `build-source`, `toolchain-cuda`, `toolchain-hip`, `toolchain-asm`,
`project-kosha25`, and `user-docs`. Feature names and defaults are defined by the project. Feature
selectors decide whether directories and dependencies participate in the project graph.

A **devtool** changes how existing targets are instrumented or checked: examples are ASan, coverage,
clang-tidy, formatting, and surrogate-header validation. Devtool names are capabilities defined by
BESA; the project only selects which ones to use. Project-specific constraints may still reject
particular combinations.

A **warning policy** modifies compiler diagnostics. Warning policies are also defined by BESA and are
composable: `essential;error` means “enable the essential warning set and promote warnings to
errors.” They do not alter project topology.

A **test mode** is a project-defined workflow selector. Tests state which modes they support, and are
built/registered only when at least one supported mode is enabled. BESA gives the names no intrinsic
meaning.

This separation keeps source build descriptions stable as project workflows and developer tooling
evolve. A future BESA version can change coverage implementation, add another warning policy, or add
a new devtool without forcing projects to rewrite target construction code. Conversely, projects can
add new feature or test-mode names without requiring changes to BESA.
