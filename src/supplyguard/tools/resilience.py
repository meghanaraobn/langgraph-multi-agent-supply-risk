"""Tool-level failure isolation, mirroring agents/resilience.py's
@safe_node pattern but for the native LangChain tools.

Every tool is supposed to return a result an LLM can read and react to,
never raise -- confirmed as an explicit design principle back in step 4
("none of the seven tools ever raise an exception to the caller"). Until
now that only held for the one case get_supplier_by_id explicitly catches
(SupplierNotFoundError); a real infrastructure hiccup (the data backend
being temporarily unreachable -- not hypothetical, hit twice for real in
this project's own development) would raise straight through every other
tool, breaking that contract and crashing the entire tool-calling loop
rather than just that one call.

Must be applied BEFORE @tool (i.e. as the innermost decorator) so
functools.wraps preserves the original function's __name__/__doc__/
__annotations__ for LangChain's schema introspection to read.
"""
from __future__ import annotations

import functools
import logging
from typing import Any, Callable

logger = logging.getLogger("supplyguard.tools")


def safe_tool(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 -- last line of defense before a tool crashes the whole agent turn
            logger.exception("Tool %s failed", func.__name__)
            return {"error": f"{func.__name__} failed: {type(exc).__name__}: {exc}"}

    return wrapper
