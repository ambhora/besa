# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
"""Small compatibility shims for Exhale releases used by BESA-generated projects."""

from __future__ import annotations


def setup(_app) -> dict[str, bool]:
    """Teach Exhale 0.3.x that Doxygen's C++20 ``concept`` kind is legitimate.

    Exhale already preserves unknown Doxygen compounds in ``all_nodes``, but its static kind list
    predates Doxygen concept support. Adding the kind suppresses the spurious "unexpected kind
    'concept'" message from its unabridged-API pass. BESA generates the actual concept pages itself
    with Breathe's ``doxygenconcept`` directive.
    """

    from exhale import utils

    if "concept" not in utils.AVAILABLE_KINDS:
        utils.AVAILABLE_KINDS.append("concept")

    return {"parallel_read_safe": True, "parallel_write_safe": True}
