import { useCallback, useRef, useState } from "react";

// Formats accepted by the backend (see ALLOWED_AUDIO_EXTENSIONS in voice.py).
// webm is what MediaRecorder produces in Chrome/Edge/Firefox by default.
const PREFERRED_MIME_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/ogg;codecs=opus",
  "audio/mp4",
];

function pickMimeType() {
  if (typeof MediaRecorder === "undefined") return null;
  return PREFERRED_MIME_TYPES.find((t) => MediaRecorder.isTypeSupported(t)) || "";
}

export function useAudioRecorder() {
  const [status, setStatus] = useState("idle"); // idle | requesting | recording | error
  const [errorMessage, setErrorMessage] = useState(null);
  const [durationSec, setDurationSec] = useState(0);

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);
  const timerRef = useRef(null);

  const start = useCallback(async () => {
    setErrorMessage(null);
    setStatus("requesting");

    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus("error");
      setErrorMessage("This browser does not support microphone recording.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType = pickMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setStatus("recording");
      setDurationSec(0);
      timerRef.current = setInterval(() => setDurationSec((d) => d + 1), 1000);
    } catch (err) {
      setStatus("error");
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setErrorMessage("Microphone access was denied. Please allow microphone permission and try again.");
      } else if (err.name === "NotFoundError") {
        setErrorMessage("No microphone was found on this device.");
      } else {
        setErrorMessage("Could not start recording. Please try again.");
      }
    }
  }, []);

  const stop = useCallback(() => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state === "inactive") {
        resolve(null);
        return;
      }
      recorder.onstop = () => {
        clearInterval(timerRef.current);
        streamRef.current?.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        setStatus("idle");
        resolve(blob);
      };
      recorder.stop();
    });
  }, []);

  const reset = useCallback(() => {
    setStatus("idle");
    setErrorMessage(null);
    setDurationSec(0);
  }, []);

  return { status, errorMessage, durationSec, start, stop, reset };
}
