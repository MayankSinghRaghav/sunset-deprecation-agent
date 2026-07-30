"""Single source of runtime configuration. Env-driven, one Settings object.

Nothing in the package reads os.environ directly; everything goes through
`settings`. That keeps the three provider modes and the two vector backends
switchable from `.env` alone, which is what makes the offline/replay story work.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LLMMode = Literal["offline", "replay", "live"]
VectorBackend = Literal["pgvector", "numpy"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SUNSET_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- database ---------------------------------------------------------
    database_url: str = (
        "postgresql+psycopg://sunset_app:sunset_app@127.0.0.1:54329/sunset"
    )
    # The scoring harness connects as sunset_eval; the app must NOT use this.
    eval_database_url: str = (
        "postgresql+psycopg://sunset_eval:sunset_eval@127.0.0.1:54329/sunset"
    )

    # --- LLM provider -----------------------------------------------------
    llm_mode: LLMMode = "offline"
    # GEMINI_API_KEY has no SUNSET_ prefix by convention (it's Google's name).
    # Read via a validation alias below.
    gemini_api_key: str = ""
    model_auditor: str = "gemini-2.5-flash"
    model_composer: str = "gemini-2.5-flash"
    embedding_model: str = "text-embedding-004"

    # --- retrieval --------------------------------------------------------
    vector_backend: VectorBackend = "pgvector"
    embedding_dim: int = 768

    # --- budget -----------------------------------------------------------
    token_budget: int = 150_000
    max_concurrency: int = 4

    # --- misc -------------------------------------------------------------
    dataset_seed: int = 1337
    dataset_version: str = "v1"

    def __init__(self, **kw):  # noqa: D401
        super().__init__(**kw)
        # GEMINI_API_KEY is conventionally un-prefixed; pull it in if the
        # prefixed form wasn't set.
        if not self.gemini_api_key:
            import os

            self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
