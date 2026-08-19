import { useCallback, useEffect, useState } from "react";
import { KeyRound, Upload, Trash2, FileText, Loader2, AlertTriangle, CheckCircle2, Lock } from "lucide-react";
import { listDocuments, uploadDocument, deleteDocument } from "../lib/api";

const ALLOWED_EXTENSIONS = [".txt", ".md", ".pdf"]; // must match documents.py ALLOWED_EXTENSIONS
const MAX_FILE_MB = 15; // must match documents.py MAX_FILE_SIZE_BYTES

export default function KnowledgeBasePage() {
  const [adminKey, setAdminKey] = useState("");
  const [unlocked, setUnlocked] = useState(false);

  const [documents, setDocuments] = useState([]);
  const [totalChunks, setTotalChunks] = useState(0);
  const [loadingList, setLoadingList] = useState(false);
  const [listError, setListError] = useState(null);

  const refresh = useCallback(async () => {
    setLoadingList(true);
    setListError(null);
    try {
      const res = await listDocuments();
      setDocuments(res.documents);
      setTotalChunks(res.total_chunks);
    } catch (err) {
      setListError(err.message);
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <div className="mb-6">
        <h2 className="font-display text-lg font-bold text-navy-700">Knowledge Base</h2>
        <p className="text-sm text-navy-400">
          The assistant can only cite what has been ingested here. Uploading and deleting
          documents requires the administrator key.
        </p>
      </div>

      <div className="card mb-6 flex items-center justify-between p-4 text-sm">
        <span className="text-navy-500">
          <span className="font-semibold text-navy-700">{documents.length}</span> document
          {documents.length === 1 ? "" : "s"} indexed &middot;{" "}
          <span className="font-semibold text-navy-700">{totalChunks}</span> chunks total
        </span>
        {loadingList && <Loader2 className="h-4 w-4 animate-spin text-navy-300" />}
      </div>

      {listError && <ErrorBanner message={listError} />}

      <DocumentList documents={documents} unlocked={unlocked} adminKey={adminKey} onChanged={refresh} />

      <div className="mt-8 border-t border-navy-100 pt-6">
        {!unlocked ? (
          <AdminUnlock adminKey={adminKey} setAdminKey={setAdminKey} onUnlock={() => setUnlocked(true)} />
        ) : (
          <UploadForm adminKey={adminKey} onUploaded={refresh} />
        )}
      </div>
    </div>
  );
}

function AdminUnlock({ adminKey, setAdminKey, onUnlock }) {
  return (
    <div className="card p-4">
      <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-navy-600">
        <Lock className="h-4 w-4" /> Administrator access
      </p>
      <p className="mb-3 text-xs text-navy-400">
        Enter the <code className="rounded bg-navy-50 px-1 py-0.5 font-mono">X-Admin-Api-Key</code> to
        upload or remove source documents. This key is sent only with document management
        requests and is never stored beyond this session.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (adminKey.trim()) onUnlock();
        }}
        className="flex gap-2"
      >
        <div className="relative flex-1">
          <KeyRound className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-navy-300" />
          <input
            type="password"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            placeholder="Admin API key"
            className="input pl-8"
            autoComplete="off"
          />
        </div>
        <button type="submit" className="btn-secondary" disabled={!adminKey.trim()}>
          Unlock
        </button>
      </form>
    </div>
  );
}

function UploadForm({ adminKey, onUploaded }) {
  const [file, setFile] = useState(null);
  const [sourceNote, setSourceNote] = useState("");
  const [status, setStatus] = useState("idle"); // idle | uploading | success | error
  const [message, setMessage] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;

    setStatus("uploading");
    setMessage(null);
    try {
      const res = await uploadDocument({ file, sourceNote: sourceNote.trim() || undefined, adminApiKey: adminKey });
      setStatus("success");
      setMessage(`"${res.document.document_name}" ingested into ${res.document.num_chunks} chunks.`);
      setFile(null);
      setSourceNote("");
      onUploaded();
    } catch (err) {
      setStatus("error");
      setMessage(err.message);
    }
  }

  return (
    <div className="card p-4">
      <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-navy-600">
        <Upload className="h-4 w-4" /> Ingest a source document
      </p>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <input
            type="file"
            accept={ALLOWED_EXTENSIONS.join(",")}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-navy-600 file:mr-3 file:rounded-sm2 file:border-0
              file:bg-navy-700 file:px-3 file:py-2 file:text-xs file:font-semibold file:text-white
              hover:file:bg-navy-600"
          />
          <p className="mt-1 text-[11px] text-navy-300">
            Allowed types: {ALLOWED_EXTENSIONS.join(", ")} &middot; max {MAX_FILE_MB} MB
          </p>
        </div>

        <input
          type="text"
          value={sourceNote}
          onChange={(e) => setSourceNote(e.target.value)}
          placeholder="Provenance note, e.g. 'doj.gov.in circular dated 12 Jan 2026' (optional)"
          className="input"
        />

        <div className="flex items-center gap-3">
          <button type="submit" disabled={!file || status === "uploading"} className="btn-primary">
            {status === "uploading" ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Ingesting…
              </>
            ) : (
              <>
                <Upload className="h-4 w-4" /> Upload &amp; index
              </>
            )}
          </button>
          {status === "success" && (
            <span className="flex items-center gap-1 text-xs text-indiagreen">
              <CheckCircle2 className="h-3.5 w-3.5" /> {message}
            </span>
          )}
          {status === "error" && (
            <span className="flex items-center gap-1 text-xs text-maroon-500">
              <AlertTriangle className="h-3.5 w-3.5" /> {message}
            </span>
          )}
        </div>
      </form>
    </div>
  );
}

function DocumentList({ documents, unlocked, adminKey, onChanged }) {
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState(null);

  async function handleDelete(documentId) {
    if (!window.confirm("Remove this document from the knowledge base? This cannot be undone.")) return;
    setDeletingId(documentId);
    setError(null);
    try {
      await deleteDocument({ documentId, adminApiKey: adminKey });
      onChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      setDeletingId(null);
    }
  }

  if (documents.length === 0) {
    return (
      <div className="rounded-sm2 border border-dashed border-navy-200 p-6 text-center text-sm text-navy-400">
        No documents indexed yet. The assistant cannot answer citizen queries until
        official DoJ source material is uploaded below.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {error && <ErrorBanner message={error} />}
      {documents.map((doc) => (
        <div key={doc.document_id} className="card flex items-center justify-between gap-3 p-3">
          <div className="flex min-w-0 items-center gap-2.5">
            <FileText className="h-4 w-4 shrink-0 text-navy-400" />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-navy-700">{doc.document_name}</p>
              <p className="truncate text-[11px] text-navy-400">
                {doc.num_chunks} chunks &middot; {(doc.char_count / 1000).toFixed(1)}k characters &middot;{" "}
                {new Date(doc.uploaded_at).toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" })}
                {doc.source_note ? ` · ${doc.source_note}` : ""}
              </p>
            </div>
          </div>
          {unlocked && (
            <button
              onClick={() => handleDelete(doc.document_id)}
              disabled={deletingId === doc.document_id}
              className="btn-danger shrink-0"
            >
              {deletingId === doc.document_id ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Trash2 className="h-3.5 w-3.5" />
              )}
              Remove
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

function ErrorBanner({ message }) {
  return (
    <div className="mb-4 flex items-center gap-2 rounded-sm2 border border-maroon-500/30 bg-maroon-500/5 px-3 py-2 text-xs text-maroon-600">
      <AlertTriangle className="h-3.5 w-3.5 shrink-0" /> {message}
    </div>
  );
}
