import { Scale } from "lucide-react";

export default function TypingIndicator() {
  return (
    <div className="flex gap-2.5">
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-navy-700">
        <Scale className="h-3.5 w-3.5 text-gold-400" />
      </div>
      <div className="flex items-center gap-2 rounded-sm2 rounded-tl-none border border-navy-100 bg-white px-4 py-3 shadow-card">
        <svg
          viewBox="0 0 24 24"
          className="h-4 w-4 animate-chakra text-navy-300"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <circle cx="12" cy="12" r="9" />
          <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" />
        </svg>
        <span className="text-xs text-navy-400">Consulting the knowledge base…</span>
      </div>
    </div>
  );
}
