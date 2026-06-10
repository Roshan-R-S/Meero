import { Copy, Trash2, X } from "lucide-react";
import { formatTime } from "../utils/formatTime";

export default function HistoryPanel({ messages, mobileOpen, onClear, onCopy, onMobileClose }) {
  if (messages.length === 0) return null;

  return (
    <>
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close conversation history"
          onClick={onMobileClose}
          className="fixed inset-0 z-40 bg-black/65 backdrop-blur-sm md:hidden"
        />
      )}
      <aside
        aria-label="Conversation history"
        className={`${mobileOpen ? "flex" : "hidden"} fixed inset-x-3 bottom-3 top-20 z-50 flex-col overflow-hidden rounded-2xl border border-cyan-400/25 bg-black/90 p-3 text-xs text-cyan-50/85 shadow-[0_0_32px_rgba(8,145,178,0.2)] backdrop-blur-xl md:absolute md:bottom-auto md:left-4 md:right-auto md:top-4 md:flex md:max-h-[60vh] md:w-64 md:bg-black/40`}
      >
        <div className="mb-3 flex items-center justify-between border-b border-cyan-400/10 pb-2">
          <span className="font-orbitron text-[0.65rem] uppercase tracking-widest text-cyan-300">History</span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={onClear}
              aria-label="Clear conversation history"
              title="Clear conversation history"
              className="grid h-7 w-7 place-items-center rounded-full text-cyan-100 transition hover:bg-cyan-900/40"
            >
              <Trash2 size={13} />
            </button>
            <button
              type="button"
              onClick={onMobileClose}
              aria-label="Close history panel"
              className="grid h-7 w-7 place-items-center rounded-full text-cyan-100 transition hover:bg-cyan-900/40 md:hidden"
            >
              <X size={14} />
            </button>
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">
          {messages.map((msg, index) => (
            <div key={`${msg.role}-${index}`} className="mb-2 flex items-start gap-2 last:mb-0">
              <div className="min-w-0 flex-1">
                <div className="mb-0.5 flex items-center gap-2">
                  <span className="text-cyan-300">{msg.role}:</span>
                  {formatTime(msg.createdAt) && (
                    <time className="text-[0.65rem] text-cyan-100/45">{formatTime(msg.createdAt)}</time>
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
      </aside>
    </>
  );
}
