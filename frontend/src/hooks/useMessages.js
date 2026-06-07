import { useCallback, useEffect, useState } from "react";
import { formatTime } from "../utils/formatTime";

const MAX_STORED_MESSAGES = 25;

const loadStoredMessages = () => {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage?.getItem?.("meero.messages");
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((message) => message?.role && typeof message.text === "string")
      .slice(-MAX_STORED_MESSAGES);
  } catch {
    return [];
  }
};

export const formatMessageTime = formatTime;

export default function useMessages() {
  const [messages, setMessages] = useState(loadStoredMessages);

  const addMessages = useCallback((nextMessages) => {
    const createdAt = new Date().toISOString();
    setMessages((prev) => [
      ...prev,
      ...nextMessages.map((message) => ({
        ...message,
        createdAt: message.createdAt || createdAt,
      })),
    ].slice(-MAX_STORED_MESSAGES));
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      if (messages.length > 0) {
        window.localStorage?.setItem?.("meero.messages", JSON.stringify(messages));
      } else {
        window.localStorage?.removeItem?.("meero.messages");
      }
    } catch {
      /* Ignore storage errors. */
    }
  }, [messages]);

  return {
    messages,
    addMessages,
    clearMessages,
  };
}
