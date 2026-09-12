import { Copy, Trash2, X } from "lucide-react";
import { useEffect, useRef } from "react";
import { formatTime } from "../utils/formatTime";
import Typewriter from "./Typewriter";

export default function HistoryPanel({ messages, mobileOpen, onClear, onCopy, onMobileClose }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    if (typeof bottomRef.current?.scrollIntoView === "function") {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

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
        className={`${
          mobileOpen ? "flex" : "hidden"
        } fixed inset-x-3 bottom-3 top-20 z-50 flex-col overflow-hidden rounded-2xl border bg-black/90 p-3 text-xs shadow-[0_0_32px_rgba(8,145,178,0.2)] backdrop-blur-xl md:absolute md:bottom-auto md:left-4 md:right-auto md:top-4 md:flex md:max-h-[60vh] md:w-64 md:bg-black/50`}
        style={{ borderColor: "var(--th-border)", color: "var(--th-text)" }}
      >
        <div className="mb-3 flex items-center justify-between border-b pb-2" style={{ borderColor: "var(--th-border)" }}>
          <span className="font-orbitron text-[0.65rem] uppercase tracking-widest font-bold" style={{ color: "var(--th-primary)" }}>
            COMM LOG
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={onClear}
              aria-label="Clear conversation history"
              title="Clear conversation history"
              className="grid h-7 w-7 place-items-center rounded-full text-neutral-400 hover:text-white transition hover:bg-white/10"
            >
              <Trash2 size={13} />
            </button>
            <button
              type="button"
              onClick={onMobileClose}
              aria-label="Close history panel"
              className="grid h-7 w-7 place-items-center rounded-full text-neutral-400 hover:text-white transition hover:bg-white/10 md:hidden"
            >
              <X size={14} />
            </button>
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto space-y-3 font-mono text-[11px] scrollbar-hide">
          {messages.map((msg, index) => {
            const key = msg.id || `${msg.role}-${msg.createdAt || index}-${index}`;

            return (
              <div key={key} className="flex items-start gap-2">
                <div className="min-w-0 flex-1">
                  <div className="mb-0.5 flex items-center gap-2">
                    <span className="uppercase font-bold text-[10px]" style={{ color: "var(--th-primary)" }}>
                      {msg.role}:
                    </span>
                    {formatTime(msg.createdAt) && (
                      <time className="text-[9px] opacity-40">{formatTime(msg.createdAt)}</time>
                    )}
                  </div>
                  <div className="break-words leading-relaxed text-neutral-200">
                    {msg.role === "assistant" && index === messages.length - 1 ? (
                      <Typewriter text={msg.text} speed={8} />
                    ) : (
                      <span>{msg.text}</span>
                    )}
                  </div>

                </div>
                <button
                  type="button"
                  onClick={() => onCopy(msg.text)}
                  aria-label={msg.role === "user" ? "Copy user prompt" : "Copy assistant response"}
                  title={msg.role === "user" ? "Copy user prompt" : "Copy assistant response"}
                  className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full text-neutral-400 hover:text-white transition hover:bg-white/10"
                >
                  <Copy size={11} />
                </button>
              </div>
            );
          })}
          <div ref={bottomRef} />
        </div>
      </aside>
    </>
  );
}
