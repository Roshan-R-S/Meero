import { RefreshCw, X } from "lucide-react";
import { formatMessageTime } from "../hooks/useMessages";

export default function SettingsPanel({
  apiHealth,
  lastHealthCheckedAt,
  onClose,
  onRefreshHealth,
  onSave,
  setVoicePitch,
  setVoiceRate,
  setWakeWordEnabled,
  voicePitch,
  voiceRate,
  wakeWordEnabled,
}) {
  return (
    <div className="absolute right-4 top-16 z-50 w-[min(21rem,calc(100vw-2rem))] rounded border border-cyan-400/25 bg-black/75 p-4 text-sm text-cyan-50 shadow-[0_0_32px_rgba(8,145,178,0.22)] backdrop-blur">
      <div className="mb-4 flex items-center justify-between">
        <span className="font-orbitron text-xs uppercase tracking-widest text-cyan-300">Settings</span>
        <button
          onClick={onClose}
          aria-label="Close settings"
          className="grid h-8 w-8 place-items-center rounded-full text-cyan-100 transition hover:bg-cyan-900/50"
        >
          <X size={16} />
        </button>
      </div>

      <label className="mb-4 flex items-center justify-between gap-4">
        <span>Wake word</span>
        <input
          type="checkbox"
          checked={wakeWordEnabled}
          onChange={(event) => setWakeWordEnabled(event.target.checked)}
          className="h-4 w-4 accent-cyan-400"
        />
      </label>

      <label className="mb-4 block">
        <span className="mb-2 flex justify-between">
          <span>Voice rate</span>
          <span>{voiceRate.toFixed(1)}</span>
        </span>
        <input
          type="range"
          min="0.5"
          max="2"
          step="0.1"
          value={voiceRate}
          onChange={(event) => setVoiceRate(Number(event.target.value))}
          className="w-full accent-cyan-400"
        />
      </label>

      <label className="mb-4 block">
        <span className="mb-2 flex justify-between">
          <span>Voice pitch</span>
          <span>{voicePitch.toFixed(1)}</span>
        </span>
        <input
          type="range"
          min="0.5"
          max="2"
          step="0.1"
          value={voicePitch}
          onChange={(event) => setVoicePitch(Number(event.target.value))}
          className="w-full accent-cyan-400"
        />
      </label>

      <div className="mb-4 grid grid-cols-2 gap-2 text-xs">
        <span className="rounded border border-cyan-400/20 px-2 py-1">
          API: {apiHealth?.status === "ok" ? "online" : "offline"}
        </span>
        <span className="rounded border border-cyan-400/20 px-2 py-1">
          Desktop: {apiHealth?.detailed ? (apiHealth?.web_safe_mode ? "safe" : "local") : "unknown"}
        </span>
        <span className="rounded border border-cyan-400/20 px-2 py-1">
          Checked: {lastHealthCheckedAt ? formatMessageTime(lastHealthCheckedAt) : "never"}
        </span>
        <button
          type="button"
          onClick={onRefreshHealth}
          aria-label="Refresh API status"
          title="Refresh API status"
          className="grid h-7 place-items-center rounded border border-cyan-400/20 text-cyan-100 transition hover:bg-cyan-900/40"
        >
          <RefreshCw size={13} />
        </button>
      </div>

      <button
        onClick={onSave}
        className="w-full rounded bg-cyan-600/90 px-3 py-2 text-sm text-white transition hover:bg-cyan-500"
      >
        Save
      </button>
    </div>
  );
}
