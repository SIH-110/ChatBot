"""
Knowledge base management.

These endpoints are how the DoJ team feeds REAL source material (circulars,
scheme descriptions, eCourts/NJDG procedure documents, POCSO Act extracts,
etc.) into the assistant. No content is ever hard-coded into the model or
invented — everything the chatbot can state as fact must first be uploaded
here from an authoritative source.

Guarded by a shared-secret admin header (see app.dependencies.require_admin).
Replace with proper RBAC before production use.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pypdf import PdfReader
import io

from app.core.exceptions import InvalidDocumentError
from app.core.logging_config import get_logger
from app.dependencies import get_rag_service, require_admin
from app.models.schemas import (
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentMetadata,
    DocumentUploadResponse,
)
from app.services.rag_service import RagService

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["Knowledge Base"])

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB


def _extract_text(filename: str, raw_bytes: bytes) -> str:
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if suffix not in ALLOWED_EXTENSIONS:
        raise InvalidDocumentError(
            f"Unsupported file type '{suffix}'. Allowed types: {sorted(ALLOWED_EXTENSIONS)}",
            details={"filename": filename},
        )

    if suffix == ".pdf":
        try:
            reader = PdfReader(io.BytesIO(raw_bytes))
            pages_text = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages_text)
        except Exception as exc:
            raise InvalidDocumentError(
                "Could not parse PDF file. It may be scanned/image-based or corrupted.",
                details={"filename": filename, "reason": str(exc)},
            ) from exc

    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidDocumentError(
            "Could not decode text file as UTF-8.", details={"filename": filename}
        ) from exc


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    dependencies=[Depends(require_admin)],
)
async def upload_document(
    rag: Annotated[RagService, Depends(get_rag_service)],
    file: UploadFile = File(..., description="A .txt, .md, or .pdf DoJ source document."),
    source_note: str | None = Form(
        default=None, description="Optional note on provenance, e.g. 'doj.gov.in circular dated ...'"
    ),
) -> DocumentUploadResponse:
    raw_bytes = await file.read()

    if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
        raise InvalidDocumentError(
            f"File exceeds the {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB limit.",
            details={"filename": file.filename},
        )

    text = _extract_text(file.filename or "unnamed", raw_bytes)
    record = rag.ingest_document(
        document_name=file.filename or "unnamed",
        text=text,
        source_note=source_note,
    )

    return DocumentUploadResponse(document=DocumentMetadata(**record.__dict__))


@router.get("/list", response_model=DocumentListResponse)
def list_documents(rag: Annotated[RagService, Depends(get_rag_service)]) -> DocumentListResponse:
    docs = rag.list_documents()
    return DocumentListResponse(
        documents=[DocumentMetadata(**d.__dict__) for d in docs],
        total_chunks=rag.total_chunks(),
    )


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    dependencies=[Depends(require_admin)],
)
def delete_document(
    document_id: str, rag: Annotated[RagService, Depends(get_rag_service)]
) -> DocumentDeleteResponse:
    deleted = rag.delete_document(document_id)
    return DocumentDeleteResponse(
        document_id=document_id,
        deleted=deleted,
        remaining_documents=len(rag.list_documents()),
    )
