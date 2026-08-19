// Mirrors app/models/schemas.py SUPPORTED_LANGUAGES exactly. If the backend
// list changes, update here too — this is intentionally not invented.
export const SUPPORTED_LANGUAGES = [
  { code: "en-IN", label: "English" },
  { code: "hi-IN", label: "Hindi" },
  { code: "bn-IN", label: "Bengali" },
  { code: "gu-IN", label: "Gujarati" },
  { code: "kn-IN", label: "Kannada" },
  { code: "ml-IN", label: "Malayalam" },
  { code: "mr-IN", label: "Marathi" },
  { code: "od-IN", label: "Odia" },
  { code: "pa-IN", label: "Punjabi" },
  { code: "ta-IN", label: "Tamil" },
  { code: "te-IN", label: "Telugu" },
  { code: "ur-IN", label: "Urdu" },
];

export function languageLabel(code) {
  return SUPPORTED_LANGUAGES.find((l) => l.code === code)?.label || code;
}
