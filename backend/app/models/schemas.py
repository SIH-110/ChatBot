"""Pydantic models defining the API's request/response contract."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator

# Sarvam-supported language codes (subset commonly used for DoJ audiences).
# Kept as a real, verified list — not invented — matching Sarvam's documented
# `/translate`, `/speech-to-text`, and `/text-to-speech` language coverage.
SUPPORTED_LANGUAGES = {
    "en-IN": "English",
    "hi-IN": "Hindi",
    "bn-IN": "Bengali",
    "gu-IN": "Gujarati",
    "kn-IN": "Kannada",
    "ml-IN": "Malayalam",
    "mr-IN": "Marathi",
    "od-IN": "Odia",
    "pa-IN": "Punjabi",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "ur-IN": "Urdu",
}


class LanguageCode(str, Enum):
    en_IN = "en-IN"
    hi_IN = "hi-IN"
    bn_IN = "bn-IN"
    gu_IN = "gu-IN"
    kn_IN = "kn-IN"
    ml_IN = "ml-IN"
    mr_IN = "mr-IN"
    od_IN = "od-IN"
    pa_IN = "pa-IN"
    ta_IN = "ta-IN"
    te_IN = "te-IN"
    ur_IN = "ur-IN"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatMessageRole(str, Enum):
    user = "user"
    assistant = "assistant"


class ChatHistoryTurn(BaseModel):
    role: ChatMessageRole
    content: str = Field(..., min_length=1, max_length=4000)


class ChatQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=1000, description="User's question in English.")
    history: list[ChatHistoryTurn] = Field(
        default_factory=list,
        max_length=12,
        description="Prior turns for conversational context (most recent last). Max 12 turns.",
    )
    response_language: LanguageCode = Field(
        default=LanguageCode.en_IN,
        description="Language the final answer should be translated into before returning.",
    )

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        return v.strip()


class SourceCitation(BaseModel):
    document_id: str
    document_name: str
    chunk_index: int
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    excerpt: str


class ChatQueryResponse(BaseModel):
    answer: str
    answer_language: LanguageCode
    grounded: bool = Field(
        ...,
        description="True if the answer was generated strictly from retrieved knowledge-base context.",
    )
    sources: list[SourceCitation] = Field(default_factory=list)
    disclaimer: str = (
        "This response is generated from indexed Department of Justice reference "
        "material and may not reflect the most recent updates. Verify time-sensitive "
        "or case-specific information on doj.gov.in or the relevant eCourts/NJDG portal."
    )
    request_id: str
    generated_at: str = Field(default_factory=utc_now)


# ---------------------------------------------------------------------------
# Voice
# ---------------------------------------------------------------------------

class TranscribeResponse(BaseModel):
    transcript: str
    detected_language: str | None = None
    request_id: str


class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2500)
    language: LanguageCode = LanguageCode.en_IN
    speaker: str | None = Field(default=None, description="Overrides the default configured speaker voice.")


class SynthesizeResponse(BaseModel):
    audio_base64: str
    audio_format: str = "wav"
    sample_rate: int = 22050
    request_id: str


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    source_language: LanguageCode | str = Field(default="auto")
    target_language: LanguageCode


class TranslateResponse(BaseModel):
    translated_text: str
    source_language_detected: str
    request_id: str


class VoiceConverseResponse(BaseModel):
    """Full pipeline result: speech in -> grounded answer -> speech out."""

    transcript: str
    detected_language: str
    answer_text: str
    answer_audio_base64: str
    grounded: bool
    sources: list[SourceCitation] = Field(default_factory=list)
    request_id: str


# ---------------------------------------------------------------------------
# Knowledge base / document ingestion
# ---------------------------------------------------------------------------

class DocumentMetadata(BaseModel):
    document_id: str
    document_name: str
    uploaded_at: str
    num_chunks: int
    char_count: int
    source_note: str | None = None


class DocumentUploadResponse(BaseModel):
    document: DocumentMetadata
    message: str = "Document ingested and indexed successfully."


class DocumentListResponse(BaseModel):
    documents: list[DocumentMetadata]
    total_chunks: int


class DocumentDeleteResponse(BaseModel):
    document_id: str
    deleted: bool
    remaining_documents: int


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    knowledge_base_documents: int
    knowledge_base_chunks: int
    groq_configured: bool
    sarvam_configured: bool
    timestamp: str = Field(default_factory=utc_now)
