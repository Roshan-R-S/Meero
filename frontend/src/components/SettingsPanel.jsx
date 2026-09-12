import { motion as Motion } from "framer-motion";
import { Check, Download, RefreshCw, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { clearMemory, exportMemory, getModelStatus } from "../api";
import { useTheme } from "../hooks/useTheme";
import { THEMES } from "../themes";
import { formatTime } from "../utils/formatTime";
import ModelStatusCard from "./ModelStatusCard";

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
  const { themeName, setTheme } = useTheme();
  const [modelStatus, setModelStatus] = useState(null);
  const [confirmClear, setConfirmClear] = useState(false);

  useEffect(() => {
    getModelStatus().then((data) => {
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
    await clearMemory();
    setConfirmClear(false);
  };

  return (
    <>
      {/* Dark backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Slide-in tactical drawer */}
      <Motion.div
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="fixed top-0 right-0 z-50 h-full w-full max-w-md bg-neutral-950/95 border-l backdrop-blur-xl p-6 flex flex-col overflow-y-auto"
        style={{ borderColor: "var(--th-border)" }}
      >
        {/* Drawer Header */}
        <div className="flex items-center justify-between pb-4 border-b" style={{ borderColor: "var(--th-border)" }}>
          <div>
            <h2 className="font-orbitron text-sm font-bold uppercase tracking-widest" style={{ color: "var(--th-text)" }}>
              Settings
            </h2>
            <span className="font-mono text-[9px] uppercase tracking-widest text-neutral-400">
              SYSTEM CONFIGURATION
            </span>
          </div>
          <button
            onClick={onClose}
            aria-label="Close settings"
            className="grid h-8 w-8 place-items-center rounded text-neutral-400 hover:text-white hover:bg-neutral-800 transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Theme Switcher Button Group */}
        <div className="my-6">
          <h3
            className="border-l-2 pl-2 mb-3 font-orbitron text-[10px] uppercase tracking-widest"
            style={{ borderColor: "var(--th-primary)", color: "var(--th-primary)" }}
          >
            TACTICAL INTERFACE THEME
          </h3>
          <div className="grid grid-cols-3 gap-2">
            {Object.values(THEMES).map((t) => (
              <button
                key={t.id}
                onClick={() => {
                  setTheme(t.id);
                  onSave({ theme: t.id });
                }}
                className={`p-2.5 rounded border text-left flex flex-col gap-1 transition-all ${
                  themeName === t.id ? "bg-white/10" : "bg-neutral-900/40 hover:bg-neutral-900"
                }`}
                style={{
                  borderColor: themeName === t.id ? t.primary : "var(--th-border)",
                  boxShadow: themeName === t.id ? `0 0 12px ${t.primary}40` : "none",
                }}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[11px] font-bold" style={{ color: t.primary }}>
                    {t.name}
                  </span>
                  {themeName === t.id && <Check className="w-3.5 h-3.5" style={{ color: t.primary }} />}
                </div>
                <span className="font-mono text-[8px] text-neutral-400 line-clamp-1">{t.subtitle}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Voice & Hardware Controls */}
        <div className="mb-6">
          <h3
            className="border-l-2 pl-2 mb-3 font-orbitron text-[10px] uppercase tracking-widest"
            style={{ borderColor: "var(--th-primary)", color: "var(--th-primary)" }}
          >
            VOICE & AUDIO CONTROLS
          </h3>

          <div className="space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between">
              <span style={{ color: "var(--th-text)" }}>Wake Word Detection</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={wakeWordEnabled}
                  onChange={(e) => setWakeWordEnabled(e.target.checked)}
                  className="sr-only peer"
                />
                <div
                  className="w-11 h-6 rounded-full transition-colors bg-neutral-800 peer-checked:bg-[var(--th-primary)]"
                />
                <span className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
              </label>
            </div>

            <div className="flex items-center justify-between">
              <span style={{ color: "var(--th-text)" }}>Microphone Active</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={micEnabled}
                  onChange={(e) => setMicEnabled(e.target.checked)}
                  className="sr-only peer"
                />
                <div
                  className="w-11 h-6 rounded-full transition-colors bg-neutral-800 peer-checked:bg-[var(--th-primary)]"
                />
                <span className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
              </label>
            </div>

            <div className="flex items-center justify-between">
              <span style={{ color: "var(--th-text)" }}>Prefer Local Voice (TTS)</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={localVoiceEnabled}
                  onChange={(e) => setLocalVoiceEnabled(e.target.checked)}
                  className="sr-only peer"
                />
                <div
                  className="w-11 h-6 rounded-full transition-colors bg-neutral-800 peer-checked:bg-[var(--th-primary)]"
                />
                <span className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
              </label>
            </div>

            <div className="flex items-center justify-between">
              <span style={{ color: "var(--th-text)" }}>Browser Speech Fallback</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={browserSpeechFallbackEnabled}
                  onChange={(e) => setBrowserSpeechFallbackEnabled(e.target.checked)}
                  className="sr-only peer"
                />
                <div
                  className="w-11 h-6 rounded-full transition-colors bg-neutral-800 peer-checked:bg-[var(--th-primary)]"
                />
                <span className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
              </label>
            </div>
          </div>
        </div>

        {/* Sliders */}
        <div className="mb-6 space-y-4 font-mono text-xs">
          <div>
            <div className="flex justify-between mb-1" style={{ color: "var(--th-text)" }}>
              <span>Voice Rate</span>
              <span>{voiceRate.toFixed(1)}x</span>
            </div>
            <input
              type="range"
              min="0.5"
              max="2"
              step="0.1"
              value={voiceRate}
              onChange={(e) => setVoiceRate(Number(e.target.value))}
              className="w-full"
              style={{ accentColor: "var(--th-primary)" }}
            />
          </div>

          <div>
            <div className="flex justify-between mb-1" style={{ color: "var(--th-text)" }}>
              <span>Voice Pitch</span>
              <span>{voicePitch.toFixed(1)}</span>
            </div>
            <input
              type="range"
              min="0.5"
              max="2"
              step="0.1"
              value={voicePitch}
              onChange={(e) => setVoicePitch(Number(e.target.value))}
              className="w-full"
              style={{ accentColor: "var(--th-primary)" }}
            />
          </div>
        </div>

        {/* UI & Display Controls */}
        <div className="mb-6">
          <h3
            className="border-l-2 pl-2 mb-3 font-orbitron text-[10px] uppercase tracking-widest"
            style={{ borderColor: "var(--th-primary)", color: "var(--th-primary)" }}
          >
            DISPLAY & INPUT
          </h3>
          <div className="space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between">
              <span style={{ color: "var(--th-text)" }}>Text Output (Subtitles)</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={textOutputEnabled}
                  onChange={(e) => setTextOutputEnabled(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 rounded-full transition-colors bg-neutral-800 peer-checked:bg-[var(--th-primary)]" />
                <span className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
              </label>
            </div>

            <div className="flex items-center justify-between">
              <span style={{ color: "var(--th-text)" }}>Show History Panel</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={showHistory}
                  onChange={(e) => setShowHistory(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 rounded-full transition-colors bg-neutral-800 peer-checked:bg-[var(--th-primary)]" />
                <span className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
              </label>
            </div>

            <div className="flex items-center justify-between">
              <span style={{ color: "var(--th-text)" }}>Text Input Field</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={textInputEnabled}
                  onChange={(e) => setTextInputEnabled(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 rounded-full transition-colors bg-neutral-800 peer-checked:bg-[var(--th-primary)]" />
                <span className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
              </label>
            </div>
          </div>
        </div>

        {/* API Telemetry Box */}
        <div className="mb-6 p-3 rounded border font-mono text-[10px] space-y-1" style={{ borderColor: "var(--th-border)" }}>
          <div className="flex justify-between">
            <span style={{ color: apiHealth?.status === "ok" ? "var(--th-primary)" : "#ef4444" }}>
              API: {apiHealth?.status === "ok" ? "online" : "offline"}
            </span>
          </div>
          <div className="flex justify-between">
            <span style={{ color: "var(--th-text)" }}>
              Desktop: {apiHealth?.detailed ? (apiHealth?.web_safe_mode ? "safe" : "local") : "unknown"}
            </span>
          </div>
          <div className="flex justify-between items-center pt-1 border-t" style={{ borderColor: "var(--th-border)" }}>
            <span className="text-neutral-400">CHECKED: {formatTime(lastHealthCheckedAt)}</span>
            <button
              onClick={onRefreshHealth}
              aria-label="Refresh API status"
              title="Refresh API status"
              className="p-1 rounded hover:bg-neutral-800"
              style={{ color: "var(--th-primary)" }}
            >
              <RefreshCw size={12} />
            </button>
          </div>
        </div>

        {/* Model Status Card */}
        <div className="mb-6">
          <h3
            className="border-l-2 pl-2 mb-3 font-orbitron text-[10px] uppercase tracking-widest"
            style={{ borderColor: "var(--th-primary)", color: "var(--th-primary)" }}
          >
            NEURAL MODELS
          </h3>
          <ModelStatusCard modelStatus={modelStatus} />
        </div>

        {/* Conversation Memory Store */}
        <div className="mb-6 p-4 rounded border bg-neutral-900/30" style={{ borderColor: "var(--th-border)" }}>
          <h4 className="font-mono text-xs font-semibold mb-1" style={{ color: "var(--th-text)" }}>
            CONVERSATION MEMORY
          </h4>
          <p className="font-mono text-[10px] text-neutral-400 mb-3">
            SQLite conversation database and short-term contextual memory.
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleExportMemory}
              className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded border text-xs font-mono transition hover:bg-neutral-800"
              style={{ borderColor: "var(--th-border)", color: "var(--th-text)" }}
            >
              <Download size={13} /> EXPORT
            </button>

            {confirmClear ? (
              <div className="flex-1 flex gap-1">
                <button
                  onClick={handleClearMemory}
                  className="flex-1 py-1.5 rounded bg-red-600 hover:bg-red-500 text-white font-mono text-xs font-bold"
                >
                  CONFIRM
                </button>
                <button
                  onClick={() => setConfirmClear(false)}
                  className="px-2 py-1.5 rounded border border-neutral-700 text-neutral-400 font-mono text-xs"
                >
                  NO
                </button>
              </div>
            ) : (
              <button
                onClick={() => setConfirmClear(true)}
                className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded border border-red-500/40 text-red-400 hover:bg-red-500/10 text-xs font-mono transition"
              >
                <Trash2 size={13} /> ERASE
              </button>
            )}
          </div>
        </div>

        {/* Save Settings */}
        <div className="mt-auto pt-4 border-t" style={{ borderColor: "var(--th-border)" }}>
          <button
            onClick={onSave}
            className="w-full py-2.5 rounded font-orbitron text-xs font-bold uppercase tracking-wider transition-all"
            style={{
              background: "var(--th-primary)",
              color: "#000000",
              boxShadow: "0 0 15px var(--th-primary-glow)",
            }}
          >
            Save
          </button>
        </div>
      </Motion.div>
    </>
  );
}
