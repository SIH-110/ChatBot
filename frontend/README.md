# DoJ Virtual Assistant — Frontend

React + Vite + Tailwind single-page app for the Department of Justice virtual
assistant. Talks directly to the FastAPI backend's `/api/v1` routes — nothing
here is mocked or invented; every request/response shape mirrors the
backend's Pydantic schemas exactly.

## 1. Install

```bash
npm install
```

## 2. Connect it to your FastAPI backend

**Local development (recommended):** leave `.env` unset. `vite.config.js`
proxies `/api/*` to `http://localhost:8000`, so just run your backend with:

```bash
uvicorn app.main:app --reload --port 8000
```

...and the frontend with:

```bash
npm run dev
```

**Pointing at a deployed backend:** copy `.env.example` to `.env` and set:

```
VITE_API_BASE_URL=https://your-backend-host
```

**Important — CORS:** your backend's `CORS_ORIGINS` setting (in `config.py` /
`.env`) must include the frontend's origin, e.g.:

```
CORS_ORIGINS=http://localhost:5173,https://your-frontend-host
```

Without this, the browser will block every request with a CORS error.

## 3. Run

```bash
npm run dev       # http://localhost:5173
npm run build      # production build to dist/
npm run preview    # preview the production build locally
```

## Feature → endpoint map

| UI area | Backend endpoint | Notes |
|---|---|---|
| Ask a Question (chat) | `POST /api/v1/chat/query` | Sends `query`, last 12 `history` turns, `response_language`. Renders `grounded`, `sources[]`, `disclaimer` exactly as returned. |
| Voice Assistant | `POST /api/v1/voice/converse` | Records mic audio via `MediaRecorder`, uploads as multipart, plays back the returned base64 WAV. |
| Knowledge Base | `GET /api/v1/documents/list`, `POST /api/v1/documents/upload`, `DELETE /api/v1/documents/{id}` | Upload/delete require the `X-Admin-Api-Key` header, entered client-side and never persisted. |
| Header status dot | `GET /api/v1/health` | Polled every 30s; reflects `groq_configured` / `sarvam_configured` / document counts. |

## Design notes

- Palette and type scale are defined once in `tailwind.config.js` (navy /
  gold / maroon on a parchment background, Merriweather display + Inter
  body) — components reference these tokens, not raw hex values.
- The "Verified from knowledge base" vs. "No matching source found" badge on
  every assistant reply mirrors the backend's `grounded` field directly —
  this is the transparency mechanism that lets a citizen see when the
  assistant is (and isn't) speaking from indexed official material.
- All 12 `SUPPORTED_LANGUAGES` in `src/lib/languages.js` are copied verbatim
  from `app/models/schemas.py`. If the backend's supported-language list
  changes, update both places.
- Constants that mirror backend validation (max query length, max history
  turns, allowed file types, max upload size) are commented with the exact
  source file/field they must stay in sync with — check those comments
  before changing backend limits.

## What's intentionally out of scope

- No client-side auth/session system — the admin key is a shared secret
  exactly as implemented in `dependencies.require_admin` on the backend.
  Replace both sides together if you move to real RBAC.
- No offline/PWA support.
- No analytics or third-party scripts.
