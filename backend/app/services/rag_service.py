"""
Retrieval-Augmented Generation service.

Design intent
-------------
This is the guardrail that keeps the assistant from inventing DoJ facts
(judge counts, procedures, deadlines, etc.). The LLM is NEVER allowed to
answer from its own parametric knowledge alone — every answer must be
grounded in text retrieved from documents the DoJ team has explicitly
uploaded. If nothing relevant is retrieved, the caller must say so rather
than guess.

Implementation notes
---------------------
Retrieval uses TF-IDF + cosine similarity (scikit-learn) rather than a
neural embedding model. This is a deliberate choice for this deployment:
it requires no external model download, no GPU, and no third-party
embedding API — it runs fully offline once installed, which matters for a
government system where the ML supply chain should be auditable and
self-contained. It is a legitimate, well-understood IR technique (this is
the same family of method that powered search engines for decades) and is
more than adequate for keyword/phrase-heavy legal & procedural text.

If the team later wants semantic (meaning-based) retrieval, this class is
the only place that needs to change — swap `_vectorize` for a sentence-
embedding model and `_similarity` for a vector index (e.g. FAISS).
"""

from __future__ import annotations

import json
import pickle
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import Settings
from app.core.exceptions import InvalidDocumentError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

INDEX_FILE = "tfidf_index.pkl"
METADATA_FILE = "documents.json"


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    document_name: str
    chunk_index: int
    text: str


@dataclass
class DocumentRecord:
    document_id: str
    document_name: str
    uploaded_at: str
    num_chunks: int
    char_count: int
    source_note: str | None = None


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float


class RagService:
    """
    Loads, persists, and queries a TF-IDF index over ingested DoJ documents.

    Not thread-safe across processes by design (single-worker deployment
    assumption for the hackathon prototype). For multi-worker production
    deployment, back this with a shared store (e.g. Redis + a proper vector
    DB) instead of local pickle files — noted in README.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._chunks: list[Chunk] = []
        self._documents: dict[str, DocumentRecord] = {}
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._load()

    # -- persistence ---------------------------------------------------

    def _index_dir(self) -> Path:
        return self._settings.kb_index_path

    def _load(self) -> None:
        index_path = self._index_dir() / INDEX_FILE
        meta_path = self._index_dir() / METADATA_FILE

        if index_path.exists():
            with open(index_path, "rb") as f:
                state = pickle.load(f)
            self._chunks = state["chunks"]
            self._vectorizer = state["vectorizer"]
            self._matrix = state["matrix"]
            logger.info("Loaded RAG index with %d chunks", len(self._chunks))
        else:
            logger.info("No existing RAG index found; starting empty.")

        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self._documents = {
                doc_id: DocumentRecord(**doc) for doc_id, doc in raw.items()
            }

    def _persist(self) -> None:
        index_path = self._index_dir() / INDEX_FILE
        meta_path = self._index_dir() / METADATA_FILE

        with open(index_path, "wb") as f:
            pickle.dump(
                {"chunks": self._chunks, "vectorizer": self._vectorizer, "matrix": self._matrix},
                f,
            )
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(
                {doc_id: doc.__dict__ for doc_id, doc in self._documents.items()},
                f,
                ensure_ascii=False,
                indent=2,
            )

    # -- chunking --------------------------------------------------------

    def _chunk_text(self, text: str) -> list[str]:
        """
        Splits text into overlapping character windows on sentence/paragraph
        boundaries where possible, so a chunk doesn't cut a clause in half.
        """
        size = self._settings.RAG_CHUNK_SIZE
        overlap = self._settings.RAG_CHUNK_OVERLAP
        text = re.sub(r"\s+", " ", text).strip()

        if len(text) <= size:
            return [text] if text else []

        sentences = re.split(r"(?<=[.!?।])\s+", text)
        chunks: list[str] = []
        current = ""

        for sentence in sentences:
            if len(current) + len(sentence) + 1 <= size:
                current = f"{current} {sentence}".strip()
            else:
                if current:
                    chunks.append(current)
                # start new chunk with overlap from the tail of the previous one
                tail = current[-overlap:] if overlap and current else ""
                current = f"{tail} {sentence}".strip()

        if current:
            chunks.append(current)

        return chunks

    # -- ingestion ---------------------------------------------------------

    def ingest_document(
        self, *, document_name: str, text: str, source_note: str | None = None
    ) -> DocumentRecord:
        if not text or not text.strip():
            raise InvalidDocumentError(
                "Document contains no extractable text.",
                details={"document_name": document_name},
            )

        chunk_texts = self._chunk_text(text)
        if not chunk_texts:
            raise InvalidDocumentError(
                "Document produced zero chunks after cleaning.",
                details={"document_name": document_name},
            )

        document_id = str(uuid.uuid4())
        from datetime import datetime, timezone

        record = DocumentRecord(
            document_id=document_id,
            document_name=document_name,
            uploaded_at=datetime.now(timezone.utc).isoformat(),
            num_chunks=len(chunk_texts),
            char_count=len(text),
            source_note=source_note,
        )

        new_chunks = [
            Chunk(
                chunk_id=f"{document_id}:{i}",
                document_id=document_id,
                document_name=document_name,
                chunk_index=i,
                text=chunk_text,
            )
            for i, chunk_text in enumerate(chunk_texts)
        ]

        self._chunks.extend(new_chunks)
        self._documents[document_id] = record
        self._rebuild_index()
        self._persist()

        logger.info(
            "Ingested document '%s' (%s) into %d chunks",
            document_name,
            document_id,
            len(chunk_texts),
        )
        return record

    def delete_document(self, document_id: str) -> bool:
        if document_id not in self._documents:
            return False

        self._chunks = [c for c in self._chunks if c.document_id != document_id]
        del self._documents[document_id]
        self._rebuild_index()
        self._persist()
        return True

    def _rebuild_index(self) -> None:
        if not self._chunks:
            self._vectorizer = None
            self._matrix = None
            return

        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            max_features=50_000,
            sublinear_tf=True,
        )
        corpus = [c.text for c in self._chunks]
        self._matrix = self._vectorizer.fit_transform(corpus)

    # -- retrieval -----------------------------------------------------

    def is_empty(self) -> bool:
        return len(self._chunks) == 0

    def list_documents(self) -> list[DocumentRecord]:
        return list(self._documents.values())

    def total_chunks(self) -> int:
        return len(self._chunks)

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        if self.is_empty() or self._vectorizer is None:
            return []

        k = top_k or self._settings.RAG_TOP_K
        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix).flatten()

        ranked_idx = np.argsort(scores)[::-1][:k]
        results = [
            RetrievedChunk(chunk=self._chunks[i], score=float(scores[i]))
            for i in ranked_idx
            if scores[i] >= self._settings.RAG_MIN_SIMILARITY
        ]
        return results
