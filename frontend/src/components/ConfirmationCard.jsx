import { motion as Motion } from "framer-motion";
import { AlertCircle, Check, X } from "lucide-react";
import { useEffect, useState } from "react";

export default function ConfirmationCard({ command, disabled, onCancel, onConfirm }) {
  const [secondsLeft, setSecondsLeft] = useState(15);


  useEffect(() => {
    if (!command) return;
    const interval = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          clearInterval(interval);
          onCancel();
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [command, onCancel]);

  if (!command) return null;

  const dashOffset = 88 - (88 * secondsLeft) / 15;

  return (
    <section
      aria-label="Action confirmation"
      className="absolute left-1/2 top-20 z-40 w-[min(28rem,calc(100vw-2rem))] -translate-x-1/2 rounded-2xl border border-amber-500/40 bg-black/90 p-5 shadow-[0_0_36px_rgba(245,158,11,0.25)] backdrop-blur-xl"
    >
      {/* 15s Countdown SVG Arc */}
      <svg className="absolute top-4 right-4 w-8 h-8 -rotate-90" viewBox="0 0 32 32">
        <circle cx="16" cy="16" r="14" fill="none" stroke="rgba(245,158,11,0.2)" strokeWidth="2.5" />
        <circle
          cx="16"
          cy="16"
          r="14"
          fill="none"
          stroke="#f59e0b"
          strokeWidth="2.5"
          strokeDasharray="88"
          strokeDashoffset={dashOffset}
        />
        <text
          x="16"
          y="19"
          textAnchor="middle"
          fill="#f59e0b"
          className="font-mono text-[9px] font-bold"
          transform="rotate(90 16 16)"
        >
          {secondsLeft}
        </text>
      </svg>

      <div className="flex items-start gap-3">
        <Motion.div
          animate={{ scale: [1, 1.15, 1] }}
          transition={{ duration: 1.5, repeat: Infinity }}
          className="mt-0.5 shrink-0 text-amber-400"
        >
          <AlertCircle size={20} />
        </Motion.div>
        <div className="min-w-0 flex-1 pr-6">
          <p className="font-orbitron text-xs uppercase tracking-widest text-amber-400 font-bold">
            CONFIRMATION REQUIRED
          </p>
          <p className="mt-2 break-words font-mono text-sm text-neutral-200">{command}</p>
          <p className="mt-1 font-mono text-[10px] text-amber-200/60">
            Review the action before allowing Meero to execute.
          </p>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={onCancel}
          disabled={disabled}
          aria-label="Cancel"
          className="flex items-center justify-center gap-2 rounded-lg border border-neutral-700 px-3 py-2 font-mono text-xs text-neutral-300 transition hover:bg-neutral-800 disabled:opacity-50"
        >
          <X size={14} />
          CANCEL
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={disabled}
          aria-label="Confirm"
          className="flex items-center justify-center gap-2 rounded-lg bg-amber-500 px-3 py-2 font-mono text-xs font-bold text-black transition hover:bg-amber-400 disabled:opacity-50 shadow-[0_0_15px_rgba(245,158,11,0.3)]"
        >
          <Check size={14} />
          CONFIRM
        </button>
      </div>

      <p className="mt-3 text-center font-mono text-[9px] tracking-wider" style={{ color: "var(--th-text-dim)" }}>
        Say &quot;confirm&quot; or &quot;cancel&quot; to respond by voice
      </p>
    </section>
  );
}
