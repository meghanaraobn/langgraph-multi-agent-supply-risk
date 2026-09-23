"""In-process pub/sub so the SSE endpoint can watch an investigation's graph
steps live, instead of a client polling GET /investigations/{id} and
manually refreshing.

A plain dict of stdlib `queue.Queue`s, not anything fancier -- this only
needs to fan out events from the one background thread running
graph.stream() for an investigation_id to however many HTTP requests are
currently watching that same id. `queue.Queue` is thread-safe by design,
which matters here: the publisher runs in FastAPI's background-task thread
pool, the subscribers are consumed from asyncio request handlers via
asyncio.to_thread. This does not survive a process restart -- an
investigation resumed after a restart falls back to the SSE endpoint's
initial snapshot-only event with no live step replay, which is acceptable
since the durable checkpoint state (already relied on by GET
/investigations/{id}) is still the source of truth for the actual result.
"""
from __future__ import annotations

import queue
import threading
from enum import Enum
from typing import Any

from pydantic import BaseModel


class InvestigationEventBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: dict[str, list[queue.Queue]] = {}

    def subscribe(self, investigation_id: str) -> queue.Queue:
        q: queue.Queue = queue.Queue()
        with self._lock:
            self._subscribers.setdefault(investigation_id, []).append(q)
        return q

    def unsubscribe(self, investigation_id: str, q: queue.Queue) -> None:
        with self._lock:
            subs = self._subscribers.get(investigation_id)
            if not subs:
                return
            if q in subs:
                subs.remove(q)
            if not subs:
                self._subscribers.pop(investigation_id, None)

    def publish(self, investigation_id: str, event: dict[str, Any]) -> None:
        with self._lock:
            subs = list(self._subscribers.get(investigation_id, ()))
        for q in subs:
            q.put(event)


bus = InvestigationEventBus()


def json_safe(value: Any) -> Any:
    """Recursively converts our domain Pydantic models / enums (the values
    LangGraph node updates actually carry) into plain JSON-serializable
    data, the same way routes.py already does one level deep with
    `.model_dump(mode="json")` for the polling response."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value
