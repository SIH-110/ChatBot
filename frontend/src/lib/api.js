import axios from "axios";

/**
 * Single axios instance for the DoJ Virtual Assistant backend.
 *
 * Base URL resolution:
 *  - In dev, Vite proxies /api -> http://localhost:8000 (see vite.config.js),
 *    so VITE_API_BASE_URL can be left unset.
 *  - In production, set VITE_API_BASE_URL to the deployed FastAPI origin
 *    (e.g. https://doj-assistant-api.example.gov.in). No trailing slash.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
const API_V1 = `${API_BASE_URL}/api/v1`;

export const client = axios.create({
  baseURL: API_V1,
  timeout: 45_000,
});

/**
 * Every error handler in the backend (app/core/exceptions.py) returns:
 *   { error: { code, message, details }, request_id }
 * This normalizes that shape (and network failures) into one Error object
 * so components never need to know the transport details.
 */
function normalizeError(err) {
  if (err.response?.data?.error) {
    const { code, message, details } = err.response.data.error;
    const e = new Error(message || "The request could not be completed.");
    e.code = code;
    e.details = details;
    e.requestId = err.response.data.request_id;
    e.status = err.response.status;
    return e;
  }
  if (err.code === "ECONNABORTED") {
    return new Error("The request timed out. The service may be under heavy load — please try again.");
  }
  if (!err.response) {
    return new Error("Could not reach the DoJ Virtual Assistant service. Check your connection and try again.");
  }
  return new Error("An unexpected error occurred. Please try again.");
}

async function call(promise) {
  try {
    const res = await promise;
    return res.data;
  } catch (err) {
    throw normalizeError(err);
  }
}

// ---------------------------------------------------------------------------
// Health — GET /api/v1/health
// ---------------------------------------------------------------------------
export function getHealth() {
  return call(client.get("/health"));
}

// ---------------------------------------------------------------------------
// Chat — POST /api/v1/chat/query
// Body: ChatQueryRequest { query, history[], response_language }
// ---------------------------------------------------------------------------
export function postChatQuery({ query, history = [], responseLanguage = "en-IN" }) {
  return call(
    client.post("/chat/query", {
      query,
      history,
      response_language: responseLanguage,
    })
  );
}

// ---------------------------------------------------------------------------
// Voice — POST /api/v1/voice/transcribe, /synthesize, /translate, /converse
// ---------------------------------------------------------------------------
export function transcribeAudio(blob, filename = "recording.webm") {
  const form = new FormData();
  form.append("file", blob, filename);
  return call(
    client.post("/voice/transcribe", form, {
      headers: { "Content-Type": "multipart/form-data" },
    })
  );
}

export function synthesizeSpeech({ text, language = "en-IN", speaker }) {
  return call(
    client.post("/voice/synthesize", {
      text,
      language,
      ...(speaker ? { speaker } : {}),
    })
  );
}

export function translateText({ text, sourceLanguage = "auto", targetLanguage }) {
  return call(
    client.post("/voice/translate", {
      text,
      source_language: sourceLanguage,
      target_language: targetLanguage,
    })
  );
}

export function voiceConverse(blob, responseLanguage = "en-IN", filename = "recording.webm") {
  const form = new FormData();
  form.append("file", blob, filename);
  form.append("response_language", responseLanguage);
  return call(
    client.post("/voice/converse", form, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 60_000,
    })
  );
}

// ---------------------------------------------------------------------------
// Knowledge base (documents) — admin-gated with X-Admin-Api-Key header
// ---------------------------------------------------------------------------
export function listDocuments() {
  return call(client.get("/documents/list"));
}

export function uploadDocument({ file, sourceNote, adminApiKey }) {
  const form = new FormData();
  form.append("file", file);
  if (sourceNote) form.append("source_note", sourceNote);
  return call(
    client.post("/documents/upload", form, {
      headers: {
        "Content-Type": "multipart/form-data",
        "X-Admin-Api-Key": adminApiKey,
      },
    })
  );
}

export function deleteDocument({ documentId, adminApiKey }) {
  return call(
    client.delete(`/documents/${documentId}`, {
      headers: { "X-Admin-Api-Key": adminApiKey },
    })
  );
}
