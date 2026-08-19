from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.config import Settings, get_settings
from app.core.rate_limiter import limiter
from app.dependencies import get_groq_service, get_rag_service, get_sarvam_service
from app.models.schemas import (
    ChatQueryRequest,
    ChatQueryResponse,
    LanguageCode,
    SourceCitation,
)
from app.services.groq_service import GroqService
from app.services.rag_service import RagService
from app.services.sarvam_service import SarvamService

router = APIRouter(prefix="/chat", tags=["Chat"])

NO_CONTEXT_ANSWER = (
    "I don't have verified information on that in my current knowledge base. "
    "For this query, please check doj.gov.in, the eCourts services portal "
    "(https://ecourts.gov.in), or the National Judicial Data Grid (NJDG) directly, "
    "or contact the relevant DoJ division."
)


@router.post("/query", response_model=ChatQueryResponse)
@limiter.limit(lambda: get_settings().RATE_LIMIT_CHAT)
async def chat_query(
    request: Request,
    payload: ChatQueryRequest,
    rag: Annotated[RagService, Depends(get_rag_service)],
    groq: Annotated[GroqService, Depends(get_groq_service)],
    sarvam: Annotated[SarvamService, Depends(get_sarvam_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatQueryResponse:
    request_id = getattr(request.state, "request_id", "-")

    retrieved = rag.retrieve(payload.query)
    grounded = len(retrieved) > 0

    if grounded:
        history_dicts = [{"role": t.role.value, "content": t.content} for t in payload.history]
        answer_en = groq.generate_grounded_answer(
            query=payload.query, retrieved_chunks=retrieved, history=history_dicts
        )
        sources = [
            SourceCitation(
                document_id=rc.chunk.document_id,
                document_name=rc.chunk.document_name,
                chunk_index=rc.chunk.chunk_index,
                similarity_score=round(rc.score, 4),
                excerpt=(rc.chunk.text[:280] + "…") if len(rc.chunk.text) > 280 else rc.chunk.text,
            )
            for rc in retrieved
        ]
    else:
        answer_en = NO_CONTEXT_ANSWER
        sources = []

    final_answer = answer_en
    if payload.response_language != LanguageCode.en_IN:
        final_answer, _ = sarvam.translate(
            text=answer_en,
            source_language_code="en-IN",
            target_language_code=payload.response_language.value,
        )

    return ChatQueryResponse(
        answer=final_answer,
        answer_language=payload.response_language,
        grounded=grounded,
        sources=sources,
        request_id=request_id,
    )
