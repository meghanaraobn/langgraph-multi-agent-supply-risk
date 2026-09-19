"""Application configuration, loaded from environment variables / .env.

Missing a required value (the Azure OpenAI credentials) fails loudly at
startup via pydantic-settings' own validation, rather than surfacing as a
confusing auth error the first time an agent tries to call the model.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_deployment: str

    weaviate_host: str = "localhost"
    weaviate_http_port: int = 8080
    weaviate_grpc_port: int = 50051
    embedding_model_name: str = "BAAI/bge-large-en-v1.5"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
