import { useState } from "react";
import { SendHorizontal } from "lucide-react";

const MIN_LEN = 2;
const MAX_LEN = 1000; // must match ChatQueryRequest.query max_length in schemas.py

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState("");

  const trimmed = value.trim();
  const tooShort = trimmed.length > 0 && trimmed.length < MIN_LEN;
  const canSend = trimmed.length >= MIN_LEN && trimmed.length <= MAX_LEN && !disabled;

  function submit() {
    if (!canSend) return;
    onSend(trimmed);
    setValue("");
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="border-t border-navy-100 bg-white p-3 sm:p-4">
      <div className="flex items-end gap-2">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
          maxLength={MAX_LEN}
          placeholder="Ask about DoJ schemes, eCourts, NJDG, legal aid, fast track courts…"
          className="input max-h-32 min-h-[44px] resize-none py-2.5 disabled:opacity-60"
        />
        <button
          onClick={submit}
          disabled={!canSend}
          className="btn-primary h-11 w-11 shrink-0 !px-0"
          aria-label="Send question"
        >
          <SendHorizontal className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-1 flex items-center justify-between px-1">
        <p className="text-[11px] text-navy-300">
          {tooShort ? (
            <span className="text-maroon-500">Please enter at least {MIN_LEN} characters.</span>
          ) : (
            "This assistant answers only from indexed official DoJ material — not general legal advice."
          )}
        </p>
        <p className="text-[11px] text-navy-300">{trimmed.length}/{MAX_LEN}</p>
      </div>
    </div>
  );
}
