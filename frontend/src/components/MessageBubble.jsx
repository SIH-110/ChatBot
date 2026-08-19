import ReactMarkdown from "react-markdown";
import { ShieldCheck, ShieldAlert, Scale, User } from "lucide-react";
import SourceCitations from "./SourceCitations";

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end gap-2.5">
        <div className="max-w-[75%] rounded-sm2 rounded-tr-none bg-navy-700 px-4 py-2.5 text-sm text-white">
          {message.content}
        </div>
        <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-navy-100">
          <User className="h-3.5 w-3.5 text-navy-500" />
        </div>
      </div>
    );
  }

  if (message.error) {
    return (
      <div className="flex gap-2.5">
        <Avatar />
        <div className="max-w-[75%] rounded-sm2 rounded-tl-none border border-maroon-500/30 bg-maroon-500/5 px-4 py-2.5 text-sm text-maroon-600">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-2.5">
      <Avatar />
      <div className="max-w-[80%] rounded-sm2 rounded-tl-none border border-navy-100 bg-white px-4 py-3 text-sm text-ink shadow-card">
        <div className="prose-sm max-w-none leading-relaxed [&_p]:mb-2 [&_p:last-child]:mb-0 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        <div className="mt-2.5 flex items-center justify-between gap-2 border-t border-navy-50 pt-2">
          <GroundedBadge grounded={message.grounded} />
          {message.requestId && (
            <span className="font-mono text-[10px] text-navy-300" title="Support reference ID">
              ref: {message.requestId.slice(0, 8)}
            </span>
          )}
        </div>

        <SourceCitations sources={message.sources} />

        {message.disclaimer && (
          <p className="mt-2.5 border-t border-navy-50 pt-2 text-[11px] leading-snug text-navy-400">
            {message.disclaimer}
          </p>
        )}
      </div>
    </div>
  );
}

function Avatar() {
  return (
    <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-navy-700">
      <Scale className="h-3.5 w-3.5 text-gold-400" />
    </div>
  );
}

function GroundedBadge({ grounded }) {
  if (grounded) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-indiagreen/10 px-2 py-0.5 text-[10px] font-semibold text-indiagreen">
        <ShieldCheck className="h-3 w-3" />
        Verified from knowledge base
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-gold-400/15 px-2 py-0.5 text-[10px] font-semibold text-gold-600">
      <ShieldAlert className="h-3 w-3" />
      No matching source found
    </span>
  );
}
