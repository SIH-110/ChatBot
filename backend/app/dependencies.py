"""
FastAPI dependency providers.

Services are instantiated once (per process) and cached, since the RAG
index and provider clients are safe to reuse across requests and creating
them per-request would be wasteful (re-reading the pickle index, etc.).
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Header

from app.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.services.groq_service import GroqService
from app.services.rag_service import RagService
from app.services.sarvam_service import SarvamService


@lru_cache
def get_rag_service() -> RagService:
    return RagService(get_settings())


@lru_cache
def get_groq_service() -> GroqService:
    return GroqService(get_settings())


@lru_cache
def get_sarvam_service() -> SarvamService:
    return SarvamService(get_settings())


def require_admin(x_admin_api_key: Annotated[str | None, Header()] = None) -> None:
    """
    Guards knowledge-base mutation endpoints (upload/delete) with a shared
    secret header. This is intentionally minimal for the hackathon
    prototype — swap for real OAuth2/JWT + role-based access control before
    any production DoJ deployment.
    """
    settings = get_settings()
    if not x_admin_api_key or x_admin_api_key != settings.ADMIN_API_KEY:
        raise UnauthorizedError("Missing or invalid X-Admin-Api-Key header.")
