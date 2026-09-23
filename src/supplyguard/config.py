"""Application configuration, loaded from environment variables / .env.

Missing a required value (the Azure OpenAI credentials) fails loudly at
startup via pydantic-settings' own validation, rather than surfacing as a
confusing auth error the first time an agent tries to call the model.

load_dotenv() below is required, not redundant with Settings' own
env_file=".env": pydantic-settings reads .env only to populate the fields
declared on Settings -- it never writes those values into os.environ. Vars
that nothing in this file declares (LANGSMITH_TRACING, LANGSMITH_API_KEY,
...) are read directly from os.environ by third-party libraries (langsmith,
langchain-core), so without this call they silently never see values that
are sitting right there in .env -- confirmed directly: os.environ lacked
LANGSMITH_TRACING even after Settings() had already loaded successfully.
"""
from __future__ import annotations

from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


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
