"""Structured observability for the investigation graph.

Two layers, deliberately not one:

1. LangSmith -- the LANGCHAIN_TRACING_V2 / LANGCHAIN_API_KEY / LANGCHAIN_PROJECT
   env vars already scaffolded in .env.example. Zero code changes: LangChain
   and LangGraph emit a full trace tree to LangSmith's dashboard automatically
   once those are set. This is the "free" baseline -- enabling it needs no
   code, only an account.
2. This module -- a custom callback handler capturing exactly the fields the
   spec names (investigation ID, agent/node, tool, latency, errors, retries,
   token usage, model calls) into our own structured log, so observability
   doesn't depend entirely on an external SaaS account existing.

Every claim below about event shapes was checked directly against this
project's actual LangGraph/LangChain versions before writing this file, not
assumed from memory:
  - investigation_id is readable directly off `inputs["investigation_id"]`
    on the per-node on_chain_start event -- LangGraph passes the node's
    InvestigationState dict as `inputs`.
  - The real node name is `metadata["langgraph_node"]`, not
    `serialized["name"]` (which is None for graph-internal chain runs).
  - Token usage and the actual model name are on
    `response.llm_output["token_usage"]` / `["model_name"]` in on_llm_end --
    not reliably available at on_llm_start.
  - Retries fire via on_retry(retry_state, ...); retry_state.attempt_number
    is the 1-indexed attempt count.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger("supplyguard.observability")


class InvestigationTracer(BaseCallbackHandler):
    """Attach via `graph.invoke(state, config={..., "callbacks": [tracer]})`.

    Emits one structured JSON log line per event and also keeps everything
    in `self.events` for immediate in-process inspection (e.g. in the
    evaluation harness or a test). A multi-process deployment would want
    these events landing in a queryable store (a Postgres table, given one
    is already running) instead of per-process memory + logs -- noted as
    the natural next step, not built here to keep this milestone's scope to
    "capture the named fields," not "build a full observability backend."
    """

    def __init__(self) -> None:
        super().__init__()
        self._start_times: dict[UUID, float] = {}
        self._investigation_ids: dict[UUID, str] = {}
        self.events: list[dict[str, Any]] = []

    # -- shared helpers ------------------------------------------------

    def _emit(self, event: dict[str, Any]) -> None:
        self.events.append(event)
        logger.info(json.dumps(event, default=str))

    def _remember_investigation_id(self, run_id: UUID, inv_id: str | None) -> None:
        if inv_id:
            self._investigation_ids[run_id] = inv_id

    def _investigation_id_for(self, run_id: UUID, parent_run_id: UUID | None) -> str | None:
        if run_id in self._investigation_ids:
            return self._investigation_ids[run_id]
        if parent_run_id is not None and parent_run_id in self._investigation_ids:
            inv_id = self._investigation_ids[parent_run_id]
            self._investigation_ids[run_id] = inv_id  # inherit for this run's own children
            return inv_id
        return None

    # -- chains == LangGraph nodes ------------------------------------------------

    def on_chain_start(
        self,
        serialized: dict[str, Any] | None,
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self._start_times[run_id] = time.time()
        inv_id = inputs.get("investigation_id") if isinstance(inputs, dict) else None
        if inv_id:
            self._remember_investigation_id(run_id, inv_id)
        else:
            inv_id = self._investigation_id_for(run_id, parent_run_id)
        node = (metadata or {}).get("langgraph_node") or (serialized or {}).get("name")
        if node is None:
            return  # internal framework-level chain wrapper, not one of our nodes
        self._emit(
            {
                "kind": "node_start",
                "investigation_id": inv_id,
                "node": node,
                "run_id": str(run_id),
            }
        )

    def on_chain_end(
        self, outputs: Any, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        start = self._start_times.pop(run_id, None)
        if start is None:
            return
        self._emit(
            {
                "kind": "node_end",
                "investigation_id": self._investigation_id_for(run_id, parent_run_id),
                "run_id": str(run_id),
                "latency_s": round(time.time() - start, 3),
            }
        )

    def on_chain_error(
        self, error: BaseException, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        self._start_times.pop(run_id, None)
        self._emit(
            {
                "kind": "node_error",
                "investigation_id": self._investigation_id_for(run_id, parent_run_id),
                "run_id": str(run_id),
                "error": f"{type(error).__name__}: {error}",
            }
        )

    # -- LLM / model calls ------------------------------------------------

    def on_llm_start(
        self,
        serialized: dict[str, Any] | None,
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        self._start_times[run_id] = time.time()
        self._emit(
            {
                "kind": "model_call_start",
                "investigation_id": self._investigation_id_for(run_id, parent_run_id),
                "run_id": str(run_id),
            }
        )

    def on_llm_end(
        self, response: Any, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        start = self._start_times.pop(run_id, None)
        latency = round(time.time() - start, 3) if start is not None else None
        llm_output = getattr(response, "llm_output", None) or {}
        self._emit(
            {
                "kind": "model_call_end",
                "investigation_id": self._investigation_id_for(run_id, parent_run_id),
                "run_id": str(run_id),
                "latency_s": latency,
                "model": llm_output.get("model_name"),
                "token_usage": llm_output.get("token_usage"),
            }
        )

    def on_llm_error(
        self, error: BaseException, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        self._start_times.pop(run_id, None)
        self._emit(
            {
                "kind": "model_call_error",
                "investigation_id": self._investigation_id_for(run_id, parent_run_id),
                "run_id": str(run_id),
                "error": f"{type(error).__name__}: {error}",
            }
        )

    def on_retry(
        self, retry_state: Any, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        self._emit(
            {
                "kind": "retry",
                "investigation_id": self._investigation_id_for(run_id, parent_run_id),
                "run_id": str(run_id),
                "attempt_number": getattr(retry_state, "attempt_number", None),
            }
        )

    # -- tool calls ------------------------------------------------

    def on_tool_start(
        self,
        serialized: dict[str, Any] | None,
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        self._start_times[run_id] = time.time()
        self._emit(
            {
                "kind": "tool_start",
                "investigation_id": self._investigation_id_for(run_id, parent_run_id),
                "run_id": str(run_id),
                "tool": (serialized or {}).get("name"),
            }
        )

    def on_tool_end(
        self, output: Any, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        start = self._start_times.pop(run_id, None)
        latency = round(time.time() - start, 3) if start is not None else None
        self._emit(
            {
                "kind": "tool_end",
                "investigation_id": self._investigation_id_for(run_id, parent_run_id),
                "run_id": str(run_id),
                "latency_s": latency,
            }
        )

    def on_tool_error(
        self, error: BaseException, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        self._start_times.pop(run_id, None)
        self._emit(
            {
                "kind": "tool_error",
                "investigation_id": self._investigation_id_for(run_id, parent_run_id),
                "run_id": str(run_id),
                "error": f"{type(error).__name__}: {error}",
            }
        )
