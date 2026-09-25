"""A tool registers its own domain at definition time, instead of
tools/__init__.py hand-maintaining a parallel list per agent -- a list that
silently goes stale if a tool is added or renamed and nobody remembers to
also update it there.

register_tool must be the outermost decorator (above @tool), so it wraps the
finished Tool object rather than the raw function -- @safe_tool still has to
stay innermost per its own docstring, for functools.wraps to preserve
schema-relevant metadata for @tool to read.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, TypeVar

_REGISTRY: dict[str, list[Any]] = defaultdict(list)

T = TypeVar("T")


def register_tool(domain: str) -> Callable[[T], T]:
    def decorator(tool_obj: T) -> T:
        _REGISTRY[domain].append(tool_obj)
        return tool_obj

    return decorator


def tools_for(domain: str) -> list[Any]:
    return list(_REGISTRY[domain])
