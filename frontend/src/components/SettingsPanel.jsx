import { RefreshCw, X, Download, Trash2 } from "lucide-react";
import { useState, useEffect } from "react";
import { exportMemory, clearMemory, getModelStatus } from "../api";
import ModelStatusCard from "./ModelStatusCard";
import { formatTime } from "../utils/formatTime";

export default function SettingsPanel({
  apiHealth,
  lastHealthCheckedAt,
  onClose,
  onRefreshHealth,
  onSave,
  setVoicePitch,
  setVoiceRate,
  setWakeWordEnabled,
  setMicEnabled,
  setTextOutputEnabled,
  setShowHistory,
  setTextInputEnabled,
  voicePitch,
  voiceRate,
  wakeWordEnabled,
  micEnabled,
  textOutputEnabled,
  showHistory,
  textInputEnabled,
  localVoiceEnabled,
  browserSpeechFallbackEnabled,
  setLocalVoiceEnabled,
  setBrowserSpeechFallbackEnabled,
}) {
  const [modelStatus, setModelStatus] = useState(null);

  useEffect(() => {
    getModelStatus().then(data => {
      if (data) setModelStatus(data);
    });
  }, []);

  const handleExportMemory = async () => {
    const data = await exportMemory();
    if (data) {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "meero_memory.json";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  const handleClearMemory = async () => {
    if (window.confirm("Are you sure you want to clear all memory? This cannot be undone.")) {
      await clearMemory();
      alert("Memory cleared.");
    }
  };

  return (
    <div className="absolute right-4 top-4 z-50 w-[min(21rem,calc(100vw-2rem))] rounded border border-cyan-400/25 bg-black/75 p-4 text-sm text-cyan-50 shadow-[0_0_32px_rgba(8,145,178,0.22)] backdrop-blur overflow-y-auto max-h-[90vh]">
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

      <div className="mb-4 flex items-center justify-between gap-4">
        <span>Wake word</span>
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={wakeWordEnabled}
            onChange={(event) => setWakeWordEnabled(event.target.checked)}
            className="sr-only peer"
            aria-label="Wake word"
          />
          <div className="w-11 h-6 bg-gray-700 rounded-full peer-checked:bg-cyan-500 transition-colors" />
          <span className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transform peer-checked:translate-x-5 transition-transform" />
        </label>
      </div>

      <div className="mb-4 flex items-center justify-between gap-4">
        <span>Microphone</span>
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={micEnabled}
            onChange={(event) => setMicEnabled(event.target.checked)}
            className="sr-only peer"
            aria-label="Microphone"
          />
          <div className="w-11 h-6 bg-gray-700 rounded-full peer-checked:bg-cyan-500 transition-colors" />
          <span className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transform peer-checked:translate-x-5 transition-transform" />
        </label>
      </div>

      <div className="mb-4 flex items-center justify-between gap-4">
        <span>Prefer local voice</span>
        <input
          type="checkbox"
          checked={localVoiceEnabled}
          onChange={(event) => setLocalVoiceEnabled(event.target.checked)}
          aria-label="Prefer local voice"
          className="accent-cyan-400"
        />
      </div>

      <div className="mb-4 flex items-center justify-between gap-4">
        <span>Browser speech fallback</span>
        <input
          type="checkbox"
          checked={browserSpeechFallbackEnabled}
          onChange={(event) => setBrowserSpeechFallbackEnabled(event.target.checked)}
          aria-label="Browser speech fallback"
          className="accent-cyan-400"
        />
      </div>

      <div className="mb-4 flex items-center justify-between gap-4">
        <span>Text output</span>
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={textOutputEnabled}
            onChange={(event) => setTextOutputEnabled(event.target.checked)}
            className="sr-only peer"
            aria-label="Text output"
          />
          <div className="w-11 h-6 bg-gray-700 rounded-full peer-checked:bg-cyan-500 transition-colors" />
          <span className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transform peer-checked:translate-x-5 transition-transform" />
        </label>
      </div>

      <div className="mb-4 flex items-center justify-between gap-4">
        <span>Show history</span>
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={showHistory}
            onChange={(event) => setShowHistory(event.target.checked)}
            className="sr-only peer"
            aria-label="Show history"
          />
          <div className="w-11 h-6 bg-gray-700 rounded-full peer-checked:bg-cyan-500 transition-colors" />
          <span className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transform peer-checked:translate-x-5 transition-transform" />
        </label>
      </div>

      <div className="mb-4 flex items-center justify-between gap-4">
        <span>Text input</span>
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={textInputEnabled}
            onChange={(event) => setTextInputEnabled(event.target.checked)}
            className="sr-only peer"
            aria-label="Text input"
          />
          <div className="w-11 h-6 bg-gray-700 rounded-full peer-checked:bg-cyan-500 transition-colors" />
          <span className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transform peer-checked:translate-x-5 transition-transform" />
        </label>
      </div>

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
          Checked: {formatTime(lastHealthCheckedAt)}
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

      <div className="mb-4">
        <h3 className="mb-2 text-xs font-orbitron uppercase text-cyan-300 tracking-widest border-b border-cyan-800 pb-1">Model Status</h3>
        <ModelStatusCard modelStatus={modelStatus} />
      </div>

      <div className="mb-4">
        <h3 className="mb-2 text-xs font-orbitron uppercase text-cyan-300 tracking-widest border-b border-cyan-800 pb-1">Memory</h3>
        <div className="flex gap-2">
          <button
            onClick={handleExportMemory}
            className="flex-1 flex items-center justify-center gap-2 rounded border border-cyan-600 px-2 py-1 text-xs transition hover:bg-cyan-900/40"
          >
            <Download size={12} /> Export
          </button>
          <button
            onClick={handleClearMemory}
            className="flex-1 flex items-center justify-center gap-2 rounded border border-red-600/50 text-red-400 px-2 py-1 text-xs transition hover:bg-red-900/40"
          >
            <Trash2 size={12} /> Clear
          </button>
        </div>
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
