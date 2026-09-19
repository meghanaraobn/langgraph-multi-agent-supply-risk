"""Node-level failure isolation.

Wraps an agent node so an unexpected failure (a transient API error, a
malformed model response, ...) becomes a normal {"errors": [...]} state
update instead of crashing the entire graph invocation. This is what makes
"one specialist failure should not automatically destroy the entire
investigation" true in practice: a parallel branch that fails still returns
a normal (if empty) update, so LangGraph's fan-in at risk_analyst proceeds
with whatever DID succeed -- confirmed live: an Azure 500 inside
sustainability_agent used to crash the whole graph.invoke() call, discarding
compliance_agent's and risk_agent's already-computed results too.

Never applied to human_review_node: interrupt() raises GraphInterrupt (a
LangGraph control-flow signal, not a real failure) internally. This
decorator explicitly re-raises anything under GraphBubbleUp, so it would not
actually break interrupts -- but a malformed human resume payload is a
client input error that should surface immediately to whoever submitted it,
not be swallowed into a silently-completed investigation.
"""
from __future__ import annotations

import functools
import logging
from typing import Callable

from langgraph.errors import GraphBubbleUp

from supplyguard.graph.state import InvestigationState, InvestigationStateUpdate

logger = logging.getLogger(__name__)

_Node = Callable[[InvestigationState], InvestigationStateUpdate]


def safe_node(node_name: str) -> Callable[[_Node], _Node]:
    def decorator(func: _Node) -> _Node:
        @functools.wraps(func)
        def wrapper(state: InvestigationState) -> InvestigationStateUpdate:
            try:
                return func(state)
            except GraphBubbleUp:
                raise  # LangGraph's own control flow -- never swallow
            except Exception as exc:  # noqa: BLE001 -- last line of defense before a node crashes the whole graph
                logger.exception("%s failed", node_name)
                return {"errors": [f"{node_name}: failed with {type(exc).__name__}: {exc}"]}

        return wrapper

    return decorator
