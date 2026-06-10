import { Check, ShieldAlert, X } from "lucide-react";

export default function ConfirmationCard({ command, disabled, onCancel, onConfirm }) {
  if (!command) return null;

  return (
    <section
      aria-label="Action confirmation"
      className="absolute left-1/2 top-20 z-40 w-[min(28rem,calc(100vw-2rem))] -translate-x-1/2 rounded-2xl border border-amber-300/35 bg-black/85 p-4 shadow-[0_0_36px_rgba(245,158,11,0.2)] backdrop-blur-xl"
    >
      <div className="flex items-start gap-3">
        <ShieldAlert className="mt-0.5 shrink-0 text-amber-300" size={20} />
        <div className="min-w-0 flex-1">
          <p className="text-xs uppercase tracking-[0.18em] text-amber-300">
            Confirmation required
          </p>
          <p className="mt-2 break-words text-sm text-white">{command}</p>
          <p className="mt-1 text-xs text-cyan-50/55">
            Review the action before allowing Meero to continue.
          </p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={onCancel}
          disabled={disabled}
          className="flex items-center justify-center gap-2 rounded-lg border border-cyan-300/20 px-3 py-2 text-sm text-cyan-50 transition hover:bg-cyan-900/35 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <X size={15} />
          Cancel
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={disabled}
          className="flex items-center justify-center gap-2 rounded-lg bg-amber-400 px-3 py-2 text-sm font-semibold text-black transition hover:bg-amber-300 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Check size={15} />
          Confirm
        </button>
      </div>
    </section>
  );
}
