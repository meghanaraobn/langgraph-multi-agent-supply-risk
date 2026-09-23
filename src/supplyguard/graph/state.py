"""Shared LangGraph state for the SupplyGuard investigation graph.

A TypedDict, not a Pydantic BaseModel -- LangGraph's runtime merges the
partial dict each node returns into this state using per-field reducers
(the Annotated[..., operator.add] fields below), a pattern built around
dict-like state. Individual field *values* are still our real Pydantic
domain models (Supplier, Finding, RiskAssessment, ...) from step 3 -- this
file only defines the container shape, not new data types.

Reducer choice matters: fields exactly one node writes (supplier,
risk_assessment, final_report) use plain overwrite -- the LangGraph default
for a key with no Annotated reducer. Fields multiple nodes could plausibly
contribute to (the three findings lists, conflicts, missing_information,
errors) use operator.add so concurrent/parallel writes (step 14) accumulate
instead of colliding, and a single failed specialist (step 18) can append to
`errors` without wiping out another specialist's findings.

TypedDict gives zero runtime validation -- confirmed directly: a node that
returns a misspelled key (e.g. "complance_findings") does not error, it is
silently dropped, and the real key it meant to update is left looking like
"the agent found nothing." LangGraph itself won't catch that. The only real
protection is static: every node function is annotated to return
InvestigationStateUpdate (below), so a misspelled or unknown key in a
returned dict literal is a mypy error at the call site, not a silent no-op
at runtime.

InvestigationState and InvestigationStateUpdate are two separate TypedDicts,
not one inherited from the other with a different `total`, because PEP 589
totality does not propagate through inheritance: a subclass's `total=False`
only applies to fields declared directly in its own body, not to fields it
inherits. A subclass that only inherits fields and sets total=False changes
nothing -- confirmed the hard way, by watching mypy still demand every key.
The two definitions below must be kept in sync by hand.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, Optional, TypedDict

from supplyguard.models import (
    Finding,
    HumanDecision,
    InvestigationPlan,
    RiskAssessment,
    Supplier,
)


def _merge_metadata(current: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    return {**current, **update}


class InvestigationState(TypedDict):
    """The full graph state -- every key required. Used for the initial
    state and as every node's input type."""

    investigation_id: str
    user_request: str

    supplier: Optional[Supplier]
    investigation_plan: Optional[InvestigationPlan]

    compliance_findings: Annotated[list[Finding], operator.add]
    risk_findings: Annotated[list[Finding], operator.add]
    sustainability_findings: Annotated[list[Finding], operator.add]
    rag_findings: Annotated[list[Finding], operator.add]

    conflicts: Annotated[list[str], operator.add]
    missing_information: Annotated[list[str], operator.add]

    risk_assessment: Optional[RiskAssessment]
    human_decision: Optional[HumanDecision]
    final_report: Optional[str]

    errors: Annotated[list[str], operator.add]
    metadata: Annotated[dict[str, Any], _merge_metadata]


class InvestigationStateUpdate(TypedDict, total=False):
    """A partial update -- any subset of keys. Every node function should
    declare this as its return type, not bare `dict`, so mypy can catch a
    misspelled or unknown key in the returned literal."""

    investigation_id: str
    user_request: str

    supplier: Optional[Supplier]
    investigation_plan: Optional[InvestigationPlan]

    compliance_findings: Annotated[list[Finding], operator.add]
    risk_findings: Annotated[list[Finding], operator.add]
    sustainability_findings: Annotated[list[Finding], operator.add]
    rag_findings: Annotated[list[Finding], operator.add]

    conflicts: Annotated[list[str], operator.add]
    missing_information: Annotated[list[str], operator.add]

    risk_assessment: Optional[RiskAssessment]
    human_decision: Optional[HumanDecision]
    final_report: Optional[str]

    errors: Annotated[list[str], operator.add]
    metadata: Annotated[dict[str, Any], _merge_metadata]


def create_initial_state(investigation_id: str, user_request: str) -> InvestigationState:
    """Builds a fresh, empty InvestigationState for a new investigation --
    avoids hand-typing all 13 keys at every call site.
    """
    return InvestigationState(
        investigation_id=investigation_id,
        user_request=user_request,
        supplier=None,
        investigation_plan=None,
        compliance_findings=[],
        risk_findings=[],
        sustainability_findings=[],
        rag_findings=[],
        conflicts=[],
        missing_information=[],
        risk_assessment=None,
        human_decision=None,
        final_report=None,
        errors=[],
        metadata={},
    )
