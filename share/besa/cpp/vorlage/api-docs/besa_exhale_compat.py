# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
"""Small compatibility shims for Exhale releases used by BESA-generated projects."""

from __future__ import annotations


def _install_cpp_parent_key_retry() -> None:
    """Retry C++ xrefs without stale lexical-scope metadata.

    Breathe creates C++ ``pending_xref`` nodes while Sphinx is parsing declarations. For some
    template specializations Sphinx 8.x can retain a ``cpp:parent_key`` whose symbol is no longer
    present in the final C++ domain symbol tree. ``CPPDomain._resolve_xref_inner`` currently asserts
    that such a parent exists, aborting the whole build instead of trying an unscoped lookup.

    Preserve normal C++-domain resolution first. Only when that exact assertion is reached and the
    node actually carries a parent key do we retry the same resolver without the stale scope. This
    keeps links whenever the globally-qualified target is resolvable and does not mask unrelated
    C++-domain assertions.
    """

    from sphinx.domains.cpp import CPPDomain

    original = CPPDomain.resolve_xref
    if getattr(original, "_besa_parent_key_retry", False):
        return

    def resolve_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        try:
            return original(self, env, fromdocname, builder, typ, target, node, contnode)
        except AssertionError:
            if "cpp:parent_key" not in node:
                raise

            # ``docutils.nodes.Element.pop()`` removes a child by integer index; it is not
            # the mapping ``dict.pop()`` operation despite element attributes supporting
            # ``node[key]`` access. Remove the Sphinx metadata from the explicit attributes
            # mapping before retrying the lookup.
            parent_key = node.attributes.pop("cpp:parent_key")
            try:
                return original(self, env, fromdocname, builder, typ, target, node, contnode)
            finally:
                node.attributes["cpp:parent_key"] = parent_key

    resolve_xref._besa_parent_key_retry = True
    CPPDomain.resolve_xref = resolve_xref


def setup(_app) -> dict[str, bool]:
    """Teach Exhale 0.3.x that Doxygen's C++20 ``concept`` kind is legitimate.

    Exhale already preserves unknown Doxygen compounds in ``all_nodes``, but its static kind list
    predates Doxygen concept support. Adding the kind suppresses the spurious "unexpected kind
    'concept'" message from its unabridged-API pass. BESA generates the actual concept pages itself
    with Breathe's ``doxygenconcept`` directive.
    """

    _install_cpp_parent_key_retry()

    from exhale import utils

    if "concept" not in utils.AVAILABLE_KINDS:
        utils.AVAILABLE_KINDS.append("concept")

    return {"parallel_read_safe": True, "parallel_write_safe": True}
