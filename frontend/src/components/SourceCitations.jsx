import { useState } from "react";
import { FileText, ChevronDown } from "lucide-react";

export default function SourceCitations({ sources }) {
  const [open, setOpen] = useState(false);
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3 rounded-sm2 border border-navy-100 bg-navy-50/50">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs font-semibold text-navy-600"
        aria-expanded={open}
      >
        <span className="flex items-center gap-1.5">
          <FileText className="h-3.5 w-3.5" />
          {sources.length} source{sources.length === 1 ? "" : "s"} from the knowledge base
        </span>
        <ChevronDown
          className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <ul className="space-y-2 border-t border-navy-100 px-3 py-2">
          {sources.map((s, i) => (
            <li key={`${s.document_id}-${s.chunk_index}`} className="text-xs">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-navy-700">
                  {i + 1}. {s.document_name}
                  <span className="ml-1 font-normal text-navy-400">
                    (chunk #{s.chunk_index})
                  </span>
                </span>
                <span className="shrink-0 rounded-full bg-navy-100 px-2 py-0.5 font-mono text-[10px] text-navy-600">
                  {(s.similarity_score * 100).toFixed(0)}% match
                </span>
              </div>
              <p className="mt-1 text-navy-500">{s.excerpt}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
