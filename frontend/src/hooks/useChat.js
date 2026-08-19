import { useCallback, useState } from "react";
import { postChatQuery } from "../lib/api";

const MAX_HISTORY_TURNS = 12; // must match ChatQueryRequest.history max_length in schemas.py

function makeId() {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;
}

export function useChat(responseLanguage) {
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);

  const sendMessage = useCallback(
    async (query) => {
      const userMsg = { id: makeId(), role: "user", content: query };
      setMessages((prev) => [...prev, userMsg]);
      setIsSending(true);

      // Build history strictly in the backend's ChatHistoryTurn shape,
      // excluding the message we just added (it's sent as `query`).
      const history = messages
        .slice(-MAX_HISTORY_TURNS)
        .map((m) => ({ role: m.role, content: m.content }));

      try {
        const res = await postChatQuery({ query, history, responseLanguage });
        setMessages((prev) => [
          ...prev,
          {
            id: makeId(),
            role: "assistant",
            content: res.answer,
            grounded: res.grounded,
            sources: res.sources,
            disclaimer: res.disclaimer,
            requestId: res.request_id,
          },
        ]);
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            id: makeId(),
            role: "assistant",
            error: true,
            content: err.message,
          },
        ]);
      } finally {
        setIsSending(false);
      }
    },
    [messages, responseLanguage]
  );

  const clearChat = useCallback(() => setMessages([]), []);

  return { messages, isSending, sendMessage, clearChat };
}
