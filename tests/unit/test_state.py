"""Guards the hand-maintained invariant documented in graph/state.py:
InvestigationState and InvestigationStateUpdate are two independently
declared TypedDicts (not one inherited from the other, since PEP 589
totality doesn't propagate through inheritance) that must carry exactly the
same fields -- one `total=True` for reading full state, the other
`total=False` for a node's partial return. Nothing in Python's type system
enforces that by itself, so a field added to one and forgotten in the other
(as happened with rag_findings) type-checks fine and only breaks at
runtime, silently, via a dropped key.
"""
from __future__ import annotations

from supplyguard.graph.state import InvestigationState, InvestigationStateUpdate


def test_state_and_update_declare_the_same_fields() -> None:
    state_fields = set(InvestigationState.__annotations__)
    update_fields = set(InvestigationStateUpdate.__annotations__)

    assert state_fields == update_fields, (
        f"InvestigationState and InvestigationStateUpdate have drifted -- "
        f"only in InvestigationState: {state_fields - update_fields or None}, "
        f"only in InvestigationStateUpdate: {update_fields - state_fields or None}"
    )
