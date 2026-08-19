import { useEffect, useRef } from "react";
import { Trash2, Scale } from "lucide-react";
import { useChat } from "../hooks/useChat";
import MessageBubble from "../components/MessageBubble";
import TypingIndicator from "../components/TypingIndicator";
import ChatInput from "../components/ChatInput";
import LanguageSelect from "../components/LanguageSelect";

const SUGGESTED_QUESTIONS = [
  "How do I check the status of my case on eCourts?",
  "What is the National Judicial Data Grid (NJDG)?",
  "How can I pay a traffic fine online?",
  "What legal aid services are available to me?",
];

export default function ChatPage({ language, onLanguageChange }) {
  const { messages, isSending, sendMessage, clearChat } = useChat(language);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isSending]);

  return (
    <div className="mx-auto flex h-[calc(100vh-116px)] max-w-3xl flex-col px-4 sm:px-6">
      <div className="flex items-center justify-between py-3">
        <p className="text-xs text-navy-400">
          {messages.length > 0 ? `${messages.length} message${messages.length === 1 ? "" : "s"}` : "New conversation"}
        </p>
        <div className="flex items-center gap-3">
          <LanguageSelect value={language} onChange={onLanguageChange} disabled={isSending} />
          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="flex items-center gap-1 text-xs font-medium text-navy-400 hover:text-maroon-500"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Clear
            </button>
          )}
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto rounded-sm2 border border-navy-100 bg-navy-50/30 p-4">
        {messages.length === 0 && (
          <EmptyState onPick={sendMessage} />
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {isSending && <TypingIndicator />}
      </div>

      <ChatInput onSend={sendMessage} disabled={isSending} />
    </div>
  );
}

function EmptyState({ onPick }) {
  return (
    <div className="flex h-full flex-col items-center justify-center px-4 py-10 text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-navy-700">
        <Scale className="h-6 w-6 text-gold-400" />
      </div>
      <h2 className="font-display text-base font-bold text-navy-700">
        Ask about DoJ services
      </h2>
      <p className="mt-1 max-w-sm text-sm text-navy-400">
        Answers are grounded strictly in official material indexed in the knowledge
        base. If nothing relevant is found, you'll be told so — not given a guess.
      </p>
      <div className="mt-5 grid w-full max-w-md gap-2 sm:grid-cols-2">
        {SUGGESTED_QUESTIONS.map((q) => (
          <button
            key={q}
            onClick={() => onPick(q)}
            className="rounded-sm2 border border-navy-100 bg-white px-3 py-2.5 text-left text-xs text-navy-600 shadow-card transition-colors hover:border-navy-300"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
