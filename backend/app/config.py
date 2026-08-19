"""
Centralized application configuration.

All tunables live here and are sourced from environment variables / a `.env`
file, never hard-coded in business logic. This keeps API keys, model names,
and RAG parameters swappable without touching code — important for a
government-facing deployment where config often differs across
dev/staging/production.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    APP_NAME: str = "DoJ Virtual Assistant API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # ---- CORS ----
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # ---- Groq ----
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_TEMPERATURE: float = 0.2
    GROQ_MAX_TOKENS: int = 1024
    GROQ_TIMEOUT_SECONDS: int = 30

    # ---- Sarvam ----
    SARVAM_API_KEY: str = ""
    SARVAM_STT_MODEL: str = "saaras:v3"
    SARVAM_TTS_MODEL: str = "bulbul:v3"
    SARVAM_TTS_SPEAKER: str = "shubh"
    SARVAM_TRANSLATE_MODEL: str = "sarvam-translate:v1"
    SARVAM_TIMEOUT_SECONDS: int = 30

    # ---- RAG / Knowledge base ----
    KB_RAW_DIR: str = "data/knowledge_base/raw"
    KB_INDEX_DIR: str = "data/knowledge_base/index"
    RAG_CHUNK_SIZE: int = 900
    RAG_CHUNK_OVERLAP: int = 150
    RAG_TOP_K: int = 4
    RAG_MIN_SIMILARITY: float = 0.08

    # ---- Admin ----
    ADMIN_API_KEY: str = "change_this_admin_key"

    # ---- Rate limiting ----
    RATE_LIMIT_CHAT: str = "20/minute"
    RATE_LIMIT_VOICE: str = "10/minute"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def kb_raw_path(self) -> Path:
        path = Path(self.KB_RAW_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def kb_index_path(self) -> Path:
        path = Path(self.KB_INDEX_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — avoids re-parsing .env on every call."""
    return Settings()
