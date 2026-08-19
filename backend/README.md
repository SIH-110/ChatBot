# DoJ Virtual Assistant — Backend (SIH1700)

FastAPI backend for the Department of Justice (Ministry of Law & Justice) chatbot/virtual
assistant. Retrieval-grounded (RAG) so the bot only states facts that exist in documents you
have uploaded — it will not invent judge counts, deadlines, fees, or procedures. Groq powers
the LLM reasoning; Sarvam powers Indian-language speech-to-text, text-to-speech, and
translation.

---

## 1. Why it's built this way

**No fact is ever hard-coded or guessed.** DoJ information (judge counts, NJDG stats, POCSO
Act procedure, fee amounts, etc.) changes and is legally sensitive — a wrong number from a DoJ
assistant is a real problem. So:

- The LLM is given a strict system prompt: answer *only* from retrieved context, and say "I
  don't know, check doj.gov.in / eCourts / NJDG" if nothing relevant was retrieved.
- If retrieval finds nothing above the similarity threshold, the backend **doesn't even call
  Groq** — it returns the "no information" response directly. This guarantees the bot cannot
  hallucinate when the knowledge base is empty or the question is out of scope.
- Every grounded answer returns its **source citations** (document name, chunk, similarity
  score, excerpt) so the frontend can show "where this came from."
- The knowledge base starts **empty**. You must upload real DoJ source material (see §4) before
  the bot can answer anything factual. This is intentional — nothing was fabricated to fill it.

**Retrieval uses TF-IDF, not a neural embedding model**, by deliberate choice: it needs no
model download, no GPU, no third-party embedding API call — everything runs locally and
auditably, which matters for a government deployment. It's the same family of technique that
powered search engines for decades and works well for keyword/phrase-heavy legal text. If you
later want semantic (meaning-based) retrieval, the only file to change is
`app/services/rag_service.py`.

---

## 2. Architecture

```
app/
├── main.py                  FastAPI app: CORS, rate limiting, request-ID tracing, error handling
├── config.py                All settings, sourced from .env — nothing hard-coded
├── dependencies.py          Shared service singletons + admin-auth guard
├── core/
│   ├── logging_config.py    Structured logging with request-id correlation
│   ├── exceptions.py        Typed domain exceptions -> consistent JSON error responses
│   └── rate_limiter.py      Shared slowapi Limiter instance
├── models/
│   └── schemas.py           Every request/response Pydantic model (the API contract)
├── services/
│   ├── rag_service.py       Chunking + TF-IDF indexing + retrieval over the knowledge base
│   ├── groq_service.py      Grounded chat completion (strict "context-only" system prompt)
│   └── sarvam_service.py    STT / TTS / Translation via the official sarvamai SDK
└── api/routes/
    ├── health.py            GET  /api/v1/health
    ├── chat.py               POST /api/v1/chat/query
    ├── voice.py              POST /api/v1/voice/transcribe, /synthesize, /translate, /converse
    └── documents.py          POST /api/v1/documents/upload · GET /list · DELETE /{id}  (admin-guarded)
```

---

## 3. Setup

```bash
cd doj_chatbot_backend
python3 -m venv .venv && source .venv/bin/activate     # optional but recommended
pip install -r requirements.txt

cp .env.example .env
# then edit .env:
#   GROQ_API_KEY=...
#   SARVAM_API_KEY=...
#   ADMIN_API_KEY=<pick a strong secret — protects document upload/delete>
#   CORS_ORIGINS=http://localhost:5173   (your React dev server, adjust for prod)

python run.py
# or: uvicorn app.main:app --reload
```

Server runs at `http://localhost:8000`. Interactive API docs (dev mode only, disabled when
`DEBUG=false`): `http://localhost:8000/docs`.

---

## 4. Loading real DoJ content (do this before demoing chat)

Upload `.txt`, `.md`, or `.pdf` files pulled from **authoritative sources** — doj.gov.in
circulars, the NJDG/eCourts public documentation, the POCSO Act text, scheme guidelines, etc.

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "X-Admin-Api-Key: <your ADMIN_API_KEY>" \
  -F "file=@doj_ecourts_overview.pdf" \
  -F "source_note=Downloaded from doj.gov.in on <date>"
```

Check what's loaded: `GET /api/v1/documents/list`. Remove something:
`DELETE /api/v1/documents/{document_id}` (also admin-guarded).

**The admin-key header is a minimal placeholder.** Before any real DoJ deployment, replace
`app.dependencies.require_admin` with proper OAuth2/JWT + role-based access control.

---

## 5. API reference

All endpoints are prefixed with `/api/v1`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Service + knowledge-base + provider-config status |
| POST | `/chat/query` | Text question → grounded answer + sources. `response_language` triggers Sarvam translation of the final answer. |
| POST | `/voice/transcribe` | Audio file → transcript (Sarvam STT, `saaras:v3`) |
| POST | `/voice/synthesize` | Text → base64 WAV audio (Sarvam TTS, `bulbul:v3`) |
| POST | `/voice/translate` | Text translation between supported Indian languages |
| POST | `/voice/converse` | Full pipeline: audio in → transcribe → translate → RAG+Groq → translate → speak → audio+text out |
| POST | `/documents/upload` | *(admin)* Ingest a source document into the knowledge base |
| GET | `/documents/list` | List indexed documents |
| DELETE | `/documents/{id}` | *(admin)* Remove a document and re-index |

Full request/response schemas: see `app/models/schemas.py`, or run the server and open
`/docs`.

### Example: chat query

```bash
curl -X POST http://localhost:8000/api/v1/chat/query \
  -H "Content-Type: application/json" \
  -d '{
        "query": "What is the eCourts Project?",
        "response_language": "hi-IN"
      }'
```

Response includes `grounded: true/false`, `sources: [...]`, and a standing `disclaimer`
pointing users to doj.gov.in/eCourts/NJDG for anything time-sensitive.

---

## 6. Supported languages (Sarvam)

`en-IN, hi-IN, bn-IN, gu-IN, kn-IN, ml-IN, mr-IN, od-IN, pa-IN, ta-IN, te-IN, ur-IN` — matches
Sarvam's documented coverage for translate/STT/TTS. Extend `SUPPORTED_LANGUAGES` /
`LanguageCode` in `app/models/schemas.py` if Sarvam adds more.

## 7. Groq model

Default model is `openai/gpt-oss-120b` (set via `GROQ_MODEL` in `.env`) — Groq's current
general-purpose model as of this build; `llama-3.3-70b-versatile` is being deprecated by Groq.
Check `console.groq.com/docs/models` if you want to switch models later — it's a one-line env
change, nothing in code needs to change.

## 8. Known limitations / next steps for production

- **Admin auth** is a shared-secret header — replace with real RBAC.
- **Single-process index**: the TF-IDF index is a local pickle file, fine for one Uvicorn
  worker. For multi-worker/production, move to a shared store (e.g. a proper vector DB).
- **No persistent chat history / user accounts** — `history` is passed per-request by the
  frontend; add a session/store layer if you want server-side conversation memory.
- **PDF extraction** uses `pypdf` text extraction — scanned/image PDFs won't extract cleanly;
  add OCR (e.g. Sarvam's Document Intelligence API) if you need to ingest scanned circulars.
- Rate limits (`RATE_LIMIT_CHAT`, `RATE_LIMIT_VOICE` in `.env`) are per-IP in-memory — swap to a
  Redis-backed limiter for multi-instance deployments.
