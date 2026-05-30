import { Copy, Trash2 } from "lucide-react";
import { formatMessageTime } from "../hooks/useMessages";

export default function HistoryPanel({ messages, onClear, onCopy }) {
  if (messages.length === 0) return null;

  return (
    <div className="absolute left-4 top-4 z-40 w-[min(20rem,calc(100vw-2rem))] max-h-64 overflow-y-auto rounded border border-cyan-400/20 bg-black/40 p-3 text-xs text-cyan-50/85 backdrop-blur">
      <div className="mb-3 flex items-center justify-between border-b border-cyan-400/10 pb-2">
        <span className="font-orbitron text-[0.65rem] uppercase tracking-widest text-cyan-300">History</span>
        <button
          type="button"
          onClick={onClear}
          aria-label="Clear conversation history"
          title="Clear conversation history"
          className="grid h-7 w-7 place-items-center rounded-full text-cyan-100 transition hover:bg-cyan-900/40"
        >
          <Trash2 size={13} />
        </button>
      </div>
      {messages.map((msg, index) => (
        <div key={`${msg.role}-${index}`} className="mb-2 flex items-start gap-2 last:mb-0">
          <div className="min-w-0 flex-1">
            <div className="mb-0.5 flex items-center gap-2">
              <span className="text-cyan-300">{msg.role}:</span>
              {formatMessageTime(msg.createdAt) && (
                <time className="text-[0.65rem] text-cyan-100/45">{formatMessageTime(msg.createdAt)}</time>
              )}
            </div>
            <span className="break-words">{msg.text}</span>
          </div>
          {msg.role === "assistant" && (
            <button
              type="button"
              onClick={() => onCopy(msg.text)}
              aria-label={`Copy assistant response ${index + 1}`}
              title="Copy response"
              className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full text-cyan-100 transition hover:bg-cyan-900/40"
            >
              <Copy size={12} />
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
