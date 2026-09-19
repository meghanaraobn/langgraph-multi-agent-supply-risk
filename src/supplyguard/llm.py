"""Factory for the LangChain chat model this project uses everywhere.

Uses ChatOpenAI (not AzureChatOpenAI) pointed at Azure AI Foundry's v1 API
surface, which is intentionally OpenAI-SDK-compatible: base_url + api_key +
model (the deployment name) is all it needs -- no separate api-version query
param, unlike the classic Azure OpenAI Chat Completions API.

The endpoint copied from the Azure portal may include a path suffix like
/responses or /chat/completions depending on which example the portal showed
-- _v1_base_url() normalizes it down to the common /openai/v1/ root either
way, so pasting the raw portal value into .env always works.

Retry is NOT centralized here via .with_retry() -- that returns a generic
RunnableRetry wrapper with no bind_tools()/with_structured_output() (checked
directly: hasattr is False for both), which every agent needs. Each call
site instead chains .with_retry() after bind_tools()/with_structured_output,
e.g. get_llm().bind_tools(TOOLS).with_retry(). `timeout` below bounds a
single attempt; retry governs what happens after one times out or fails.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_openai import ChatOpenAI

from supplyguard.config import get_settings


def _v1_base_url(endpoint: str) -> str:
    return endpoint.split("/openai/v1")[0] + "/openai/v1/"


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        base_url=_v1_base_url(settings.azure_openai_endpoint),
        api_key=settings.azure_openai_api_key,
        model=settings.azure_openai_deployment,
        timeout=60,
    )
