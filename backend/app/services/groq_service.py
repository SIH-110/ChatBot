"""
Groq service — handles core LLM reasoning/chat.

The system prompt is the single most important piece of this file for a
DoJ deployment: it hard-constrains the model to answer only from supplied
context and to explicitly decline when context is insufficient, rather
than filling gaps with plausible-sounding but unverified specifics
(judge counts, deadlines, fees, etc.).
"""

from __future__ import annotations

from groq import Groq, APIError, APIConnectionError, APITimeoutError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import Settings
from app.core.exceptions import UpstreamProviderError
from app.core.logging_config import get_logger
from app.services.rag_service import RetrievedChunk

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the official virtual assistant for the Department of Justice \
(DoJ), Ministry of Law & Justice, Government of India. You help citizens understand DoJ \
schemes, eCourts, the National Judicial Data Grid (NJDG), judicial appointments, legal aid, \
Fast Track Special Courts, and related public services.

STRICT RULES — follow every one of these without exception:
1. Answer ONLY using the information given to you in the "CONTEXT" section below. Do not use \
outside knowledge, training data, or assumptions to fill in facts — especially numbers \
(judge counts, vacancies, fees, dates, deadlines, statistics) and procedural steps.
2. If the CONTEXT does not contain enough information to answer the question, say so plainly \
and tell the user where they may be able to find it (e.g. "the eCourts portal," "the NJDG \
dashboard," "doj.gov.in") — do NOT guess or approximate an answer.
3. Never state a specific number, date, fee amount, or legal citation unless it appears \
verbatim or is directly derivable from the CONTEXT.
4. Keep answers clear, concise, and in plain language suitable for a citizen who may not have \
a legal background. Use short paragraphs or bullet points for multi-step procedures.
5. Do not offer legal advice or predict case outcomes. For anything case-specific, direct the \
user to the appropriate eCourts service, a legal aid authority, or a qualified advocate.
6. Maintain a neutral, respectful, official tone at all times.
7. If asked something entirely unrelated to DoJ/justice-system services, politely explain that \
you can only help with Department of Justice related queries.
"""


def _build_context_block(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(No relevant context was retrieved from the knowledge base.)"

    parts = []
    for rc in chunks:
        parts.append(
            f"[Source: {rc.chunk.document_name} | chunk #{rc.chunk.chunk_index} | "
            f"relevance={rc.score:.2f}]\n{rc.chunk.text}"
        )
    return "\n\n---\n\n".join(parts)


class GroqService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = Groq(api_key=settings.GROQ_API_KEY, timeout=settings.GROQ_TIMEOUT_SECONDS)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((APIConnectionError, APITimeoutError)),
    )
    def _call_groq(self, messages: list[dict]) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._settings.GROQ_MODEL,
                messages=messages,
                temperature=self._settings.GROQ_TEMPERATURE,
                max_tokens=self._settings.GROQ_MAX_TOKENS,
            )
        except (APIConnectionError, APITimeoutError):
            raise
        except APIError as exc:
            logger.error("Groq API error: %s", exc)
            raise UpstreamProviderError(
                "The language model provider (Groq) returned an error.",
                details={"provider": "groq", "reason": str(exc)},
            ) from exc

        content = response.choices[0].message.content
        if not content:
            raise UpstreamProviderError(
                "The language model returned an empty response.",
                details={"provider": "groq"},
            )
        return content.strip()

    def generate_grounded_answer(
        self,
        *,
        query: str,
        retrieved_chunks: list[RetrievedChunk],
        history: list[dict] | None = None,
    ) -> str:
        context_block = _build_context_block(retrieved_chunks)

        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for turn in (history or [])[-8:]:
            messages.append(turn)

        messages.append(
            {
                "role": "user",
                "content": (
                    f"CONTEXT:\n{context_block}\n\n"
                    f"USER QUESTION:\n{query}\n\n"
                    "Answer strictly per the system rules, using only the CONTEXT above."
                ),
            }
        )

        try:
            return self._call_groq(messages)
        except (APIConnectionError, APITimeoutError) as exc:
            logger.error("Groq connection/timeout error: %s", exc)
            raise UpstreamProviderError(
                "Could not reach the language model provider (Groq). Please try again.",
                details={"provider": "groq", "reason": str(exc)},
            ) from exc
