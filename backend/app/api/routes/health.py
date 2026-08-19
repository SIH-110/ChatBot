from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.dependencies import get_rag_service
from app.models.schemas import HealthResponse
from app.services.rag_service import RagService

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check(
    settings: Annotated[Settings, Depends(get_settings)],
    rag: Annotated[RagService, Depends(get_rag_service)],
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        knowledge_base_documents=len(rag.list_documents()),
        knowledge_base_chunks=rag.total_chunks(),
        groq_configured=bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY != "your_groq_api_key_here"),
        sarvam_configured=bool(settings.SARVAM_API_KEY and settings.SARVAM_API_KEY != "your_sarvam_api_key_here"),
    )
