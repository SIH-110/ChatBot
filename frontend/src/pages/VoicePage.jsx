import { useEffect, useRef, useState } from "react";
import { Mic, Square, Loader2, Volume2, AlertTriangle } from "lucide-react";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import { voiceConverse } from "../lib/api";
import LanguageSelect from "../components/LanguageSelect";
import SourceCitations from "../components/SourceCitations";
import { languageLabel } from "../lib/languages";

export default function VoicePage({ language, onLanguageChange }) {
  const { status, errorMessage, durationSec, start, stop } = useAudioRecorder();
  const [phase, setPhase] = useState("idle"); // idle | recording | processing | done | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const audioRef = useRef(null);

  useEffect(() => {
    if (status === "recording") setPhase("recording");
  }, [status]);

  useEffect(() => {
    if (result?.answer_audio_base64 && audioRef.current) {
      audioRef.current.play().catch(() => {
        // Autoplay can be blocked — the visible play button below still works.
      });
    }
  }, [result]);

  async function handleStart() {
    setResult(null);
    setError(null);
    await start();
  }

  async function handleStop() {
    const blob = await stop();
    if (!blob || blob.size === 0) {
      setPhase("idle");
      return;
    }
    setPhase("processing");
    try {
      const res = await voiceConverse(blob, language);
      setResult(res);
      setPhase("done");
    } catch (err) {
      setError(err.message);
      setPhase("error");
    }
  }

  const audioSrc = result?.answer_audio_base64
    ? `data:audio/wav;base64,${result.answer_audio_base64}`
    : null;

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="font-display text-lg font-bold text-navy-700">Voice Assistant</h2>
          <p className="text-sm text-navy-400">
            Speak your question in any supported Indian language.
          </p>
        </div>
        <LanguageSelect value={language} onChange={onLanguageChange} disabled={phase === "recording" || phase === "processing"} />
      </div>

      <div className="card flex flex-col items-center gap-4 p-8">
        <RecordButton phase={phase} durationSec={durationSec} onStart={handleStart} onStop={handleStop} />

        {phase === "recording" && (
          <p className="text-sm font-medium text-maroon-500">
            Recording… {formatDuration(durationSec)} — tap the square to finish
          </p>
        )}
        {phase === "processing" && (
          <p className="flex items-center gap-2 text-sm text-navy-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            Transcribing, retrieving context, and generating a grounded reply…
          </p>
        )}
        {errorMessage && phase !== "recording" && (
          <p className="flex items-center gap-2 text-sm text-maroon-500">
            <AlertTriangle className="h-4 w-4" /> {errorMessage}
          </p>
        )}
        {error && (
          <p className="flex items-center gap-2 text-sm text-maroon-500">
            <AlertTriangle className="h-4 w-4" /> {error}
          </p>
        )}
      </div>

      {result && (
        <div className="mt-6 space-y-4">
          <TranscriptCard label="You said" text={result.transcript} meta={languageLabel(result.detected_language)} />

          <div className="card p-4">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-navy-400">
                Assistant reply
              </p>
              {result.grounded ? (
                <span className="rounded-full bg-indiagreen/10 px-2 py-0.5 text-[10px] font-semibold text-indiagreen">
                  Verified from knowledge base
                </span>
              ) : (
                <span className="rounded-full bg-gold-400/15 px-2 py-0.5 text-[10px] font-semibold text-gold-600">
                  No matching source found
                </span>
              )}
            </div>
            <p className="text-sm leading-relaxed text-ink">{result.answer_text}</p>

            {audioSrc && (
              <div className="mt-3 flex items-center gap-2 border-t border-navy-50 pt-3">
                <Volume2 className="h-4 w-4 text-navy-400" />
                <audio ref={audioRef} controls src={audioSrc} className="h-9 w-full" />
              </div>
            )}

            <SourceCitations sources={result.sources} />
          </div>
        </div>
      )}
    </div>
  );
}

function RecordButton({ phase, durationSec, onStart, onStop }) {
  const isRecording = phase === "recording";
  const isProcessing = phase === "processing";

  return (
    <button
      onClick={isRecording ? onStop : onStart}
      disabled={isProcessing}
      aria-label={isRecording ? "Stop recording" : "Start recording"}
      className={[
        "flex h-20 w-20 items-center justify-center rounded-full transition-all",
        isRecording
          ? "bg-maroon-500 shadow-[0_0_0_8px_rgba(139,30,63,0.12)]"
          : "bg-navy-700 hover:bg-navy-600",
        isProcessing ? "cursor-not-allowed opacity-50" : "",
      ].join(" ")}
    >
      {isProcessing ? (
        <Loader2 className="h-7 w-7 animate-spin text-white" />
      ) : isRecording ? (
        <Square className="h-6 w-6 fill-white text-white" />
      ) : (
        <Mic className="h-7 w-7 text-gold-400" />
      )}
    </button>
  );
}

function TranscriptCard({ label, text, meta }) {
  return (
    <div className="card p-4">
      <div className="mb-1 flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-navy-400">{label}</p>
        {meta && <p className="text-[11px] text-navy-300">{meta}</p>}
      </div>
      <p className="text-sm text-ink">{text}</p>
    </div>
  );
}

function formatDuration(sec) {
  const m = Math.floor(sec / 60).toString().padStart(2, "0");
  const s = (sec % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}
