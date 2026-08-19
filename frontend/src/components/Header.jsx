import { Scale, CircleDot } from "lucide-react";

export default function Header({ activeTab, onTabChange, health }) {
  const tabs = [
    { id: "chat", label: "Ask a Question" },
    { id: "voice", label: "Voice Assistant" },
    { id: "knowledge-base", label: "Knowledge Base" },
  ];

  return (
    <header className="sticky top-0 z-40 bg-white">
      <div className="tricolor-bar" />
      <div className="border-b border-navy-100">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-navy-700">
              <Scale className="h-5 w-5 text-gold-400" strokeWidth={2} />
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-navy-400">
                Government of India &middot; Ministry of Law &amp; Justice
              </p>
              <h1 className="font-display text-lg font-bold leading-tight text-navy-800 sm:text-xl">
                Department of Justice — Virtual Assistant
              </h1>
            </div>
          </div>

          <HealthBadge health={health} />
        </div>

        <nav className="mx-auto flex max-w-6xl gap-1 px-4 sm:px-6" aria-label="Primary">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={[
                "relative px-4 py-3 text-sm font-semibold transition-colors",
                activeTab === tab.id
                  ? "text-navy-700"
                  : "text-navy-400 hover:text-navy-600",
              ].join(" ")}
              aria-current={activeTab === tab.id ? "page" : undefined}
            >
              {tab.label}
              {activeTab === tab.id && (
                <span className="absolute inset-x-3 -bottom-px h-[3px] rounded-full bg-gold-400" />
              )}
            </button>
          ))}
        </nav>
      </div>
    </header>
  );
}

function HealthBadge({ health }) {
  if (!health) {
    return (
      <div className="hidden items-center gap-1.5 text-xs text-navy-300 sm:flex">
        <CircleDot className="h-3 w-3 animate-pulse" />
        Checking service status…
      </div>
    );
  }

  const ok = health.status === "ok";
  return (
    <div
      className="hidden items-center gap-1.5 text-xs font-medium text-navy-500 sm:flex"
      title={`Groq (reasoning): ${health.groq_configured ? "configured" : "not configured"} · Sarvam (voice): ${health.sarvam_configured ? "configured" : "not configured"}`}
    >
      <span
        className={[
          "h-2 w-2 rounded-full",
          ok ? "bg-indiagreen" : "bg-maroon-500",
        ].join(" ")}
      />
      {ok ? "Service operational" : "Service degraded"}
      <span className="text-navy-300">
        &middot; {health.knowledge_base_documents} document
        {health.knowledge_base_documents === 1 ? "" : "s"} indexed
      </span>
    </div>
  );
}
