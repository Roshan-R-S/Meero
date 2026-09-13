import { motion as Motion, AnimatePresence } from "framer-motion";
import Typewriter from "./Typewriter";

export default function SubtitleBar({ messages = [], enabled = true, assistantName = "MEERO" }) {
  if (!enabled || !messages || messages.length === 0) return null;

  const lastUserMessage = [...messages].reverse().find((m) => m.role === "user");
  const lastAssistantMessage = [...messages].reverse().find((m) => m.role === "assistant");

  if (!lastUserMessage && !lastAssistantMessage) return null;

  const currentKey = (lastAssistantMessage?.createdAt || "") + (lastUserMessage?.createdAt || "");

  return (
    <AnimatePresence mode="wait">
      <Motion.div
        key={currentKey}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -6 }}
        transition={{ duration: 0.2 }}
        className="w-full max-w-lg px-3.5 py-2.5 rounded-lg border backdrop-blur-md z-20 my-2 shadow-lg"
        style={{
          background: "rgba(10, 14, 23, 0.75)",
          borderColor: "var(--th-border)",
          boxShadow: "0 0 16px var(--th-primary-subtle)",
        }}
        data-testid="subtitle-bar"
      >
        {lastUserMessage && (
          <div
            className="flex items-baseline gap-2 font-mono text-[11px] mb-1"
            style={{ color: "var(--th-text-dim)" }}
          >
            <span className="font-bold tracking-wider select-none shrink-0" style={{ color: "var(--th-primary)" }}>
              YOU ›
            </span>
            <span className="truncate">{lastUserMessage.text}</span>
          </div>
        )}

        {lastAssistantMessage && (
          <div className="flex items-start gap-2 text-xs md:text-sm" style={{ color: "var(--th-text)" }}>
            <span
              className="font-orbitron text-[10px] font-bold tracking-widest shrink-0 mt-0.5 select-none"
              style={{ color: "var(--th-primary)" }}
            >
              {`${assistantName.toUpperCase()} ›`}
            </span>
            <div className="flex-1 font-sans leading-relaxed break-words [&_p]:m-0">
              <Typewriter
                key={lastAssistantMessage.createdAt || lastAssistantMessage.text}
                text={lastAssistantMessage.text}
                speed={10}
              />
            </div>
          </div>
        )}
      </Motion.div>
    </AnimatePresence>
  );
}
