from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from app.config import get_settings
from app.core.exceptions import InvalidDocumentError
from app.core.rate_limiter import limiter
from app.dependencies import get_groq_service, get_rag_service, get_sarvam_service
from app.models.schemas import (
    LanguageCode,
    SourceCitation,
    SynthesizeRequest,
    SynthesizeResponse,
    TranscribeResponse,
    TranslateRequest,
    TranslateResponse,
    VoiceConverseResponse,
)
from app.services.groq_service import GroqService
from app.services.rag_service import RagService
from app.services.sarvam_service import SarvamService

router = APIRouter(prefix="/voice", tags=["Voice"])

MAX_AUDIO_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
ALLOWED_AUDIO_EXTENSIONS = {
    "wav", "mp3", "aac", "aiff", "ogg", "opus", "flac", "mp4", "m4a", "amr", "wma", "webm", "pcm",
}


def _validate_audio(file: UploadFile, raw_bytes: bytes) -> None:
    if len(raw_bytes) > MAX_AUDIO_SIZE_BYTES:
        raise InvalidDocumentError(
            f"Audio file exceeds the {MAX_AUDIO_SIZE_BYTES // (1024 * 1024)} MB limit."
        )
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if ext and ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise InvalidDocumentError(
            f"Unsupported audio format '.{ext}'.",
            details={"allowed": sorted(ALLOWED_AUDIO_EXTENSIONS)},
        )


@router.post("/transcribe", response_model=TranscribeResponse)
@limiter.limit(lambda: get_settings().RATE_LIMIT_VOICE)
async def transcribe_audio(
    request: Request,
    sarvam: Annotated[SarvamService, Depends(get_sarvam_service)],
    file: UploadFile = File(..., description="Audio clip to transcribe (<=30s for REST API)."),
) -> TranscribeResponse:
    request_id = getattr(request.state, "request_id", "-")
    raw_bytes = await file.read()
    _validate_audio(file, raw_bytes)

    transcript, detected_language = sarvam.transcribe(
        audio_bytes=raw_bytes, filename=file.filename or "audio.wav"
    )
    return TranscribeResponse(transcript=transcript, detected_language=detected_language, request_id=request_id)


@router.post("/synthesize", response_model=SynthesizeResponse)
@limiter.limit(lambda: get_settings().RATE_LIMIT_VOICE)
async def synthesize_speech(
    request: Request,
    payload: SynthesizeRequest,
    sarvam: Annotated[SarvamService, Depends(get_sarvam_service)],
) -> SynthesizeResponse:
    request_id = getattr(request.state, "request_id", "-")
    audio_b64, sample_rate = sarvam.synthesize(
        text=payload.text, language_code=payload.language.value, speaker=payload.speaker
    )
    return SynthesizeResponse(audio_base64=audio_b64, sample_rate=sample_rate, request_id=request_id)


@router.post("/translate", response_model=TranslateResponse)
@limiter.limit(lambda: get_settings().RATE_LIMIT_VOICE)
async def translate_text(
    request: Request,
    payload: TranslateRequest,
    sarvam: Annotated[SarvamService, Depends(get_sarvam_service)],
) -> TranslateResponse:
    request_id = getattr(request.state, "request_id", "-")
    source_code = (
        payload.source_language.value
        if isinstance(payload.source_language, LanguageCode)
        else payload.source_language
    )
    translated_text, detected_source = sarvam.translate(
        text=payload.text,
        source_language_code=source_code,
        target_language_code=payload.target_language.value,
    )
    return TranslateResponse(
        translated_text=translated_text,
        source_language_detected=detected_source,
        request_id=request_id,
    )


@router.post("/converse", response_model=VoiceConverseResponse)
@limiter.limit(lambda: get_settings().RATE_LIMIT_VOICE)
async def voice_converse(
    request: Request,
    rag: Annotated[RagService, Depends(get_rag_service)],
    groq: Annotated[GroqService, Depends(get_groq_service)],
    sarvam: Annotated[SarvamService, Depends(get_sarvam_service)],
    file: UploadFile = File(..., description="Spoken question, any supported Indian language."),
    response_language: LanguageCode = Form(default=LanguageCode.en_IN),
) -> VoiceConverseResponse:
    """
    Full voice pipeline: audio -> transcript -> (translate to English if needed)
    -> RAG-grounded Groq answer -> translate back -> speech.
    """
    request_id = getattr(request.state, "request_id", "-")
    raw_bytes = await file.read()
    _validate_audio(file, raw_bytes)

    transcript, detected_language = sarvam.transcribe(
        audio_bytes=raw_bytes, filename=file.filename or "audio.wav"
    )
    detected_language = detected_language or "en-IN"

    query_en = transcript
    if detected_language != "en-IN":
        query_en, _ = sarvam.translate(
            text=transcript, source_language_code=detected_language, target_language_code="en-IN"
        )

    retrieved = rag.retrieve(query_en)
    grounded = len(retrieved) > 0

    if grounded:
        answer_en = groq.generate_grounded_answer(query=query_en, retrieved_chunks=retrieved)
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
        answer_en = (
            "I don't have verified information on that in my current knowledge base. "
            "Please check doj.gov.in or the eCourts/NJDG portal directly."
        )
        sources = []

    answer_final = answer_en
    if response_language != LanguageCode.en_IN:
        answer_final, _ = sarvam.translate(
            text=answer_en, source_language_code="en-IN", target_language_code=response_language.value
        )

    answer_audio_b64, _ = sarvam.synthesize(text=answer_final, language_code=response_language.value)

    return VoiceConverseResponse(
        transcript=transcript,
        detected_language=detected_language,
        answer_text=answer_final,
        answer_audio_base64=answer_audio_b64,
        grounded=grounded,
        sources=sources,
        request_id=request_id,
    )
