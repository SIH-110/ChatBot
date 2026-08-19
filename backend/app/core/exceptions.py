"""
Domain-specific exceptions and their FastAPI handlers.

Keeping exceptions typed (rather than raising bare HTTPException everywhere)
means callers can distinguish "upstream provider failed" from "no relevant
knowledge base content" from "bad input" — and the frontend can render each
differently instead of a generic error toast.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class DojAssistantError(Exception):
    """Base class for all application-raised errors."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "internal_error"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class UpstreamProviderError(DojAssistantError):
    """Raised when Groq or Sarvam returns an error or times out."""

    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "upstream_provider_error"


class NoRelevantContextError(DojAssistantError):
    """
    Raised when the knowledge base has no chunk similar enough to the query.

    This is intentionally surfaced as a distinct, honest response rather than
    letting the LLM guess — for a DoJ-facing assistant, "I don't know" is a
    correct answer and fabricated specifics are not acceptable.
    """

    status_code = status.HTTP_200_OK
    error_code = "no_relevant_context"


class EmptyKnowledgeBaseError(DojAssistantError):
    status_code = status.HTTP_200_OK
    error_code = "empty_knowledge_base"


class InvalidDocumentError(DojAssistantError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "invalid_document"


class UnauthorizedError(DojAssistantError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "unauthorized"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DojAssistantError)
    async def handle_domain_error(request: Request, exc: DojAssistantError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "-")
        logger.warning(
            "%s: %s | details=%s",
            exc.error_code,
            exc.message,
            exc.details,
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                },
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "-")
        logger.exception("Unhandled exception", extra={"request_id": request_id})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred. Please try again.",
                    "details": {},
                },
                "request_id": request_id,
            },
        )
