import { motion as Motion } from "framer-motion";
import { Activity, Mic, MicOff, RefreshCw } from "lucide-react";
import CommandInput from "./CommandInput";

export default function VoiceControls({
  browserFallbackEnabled,
  browserSpeechSupported,
  localVoiceAvailable,
  localVoiceEnabled,
  micEnabled,
  onBrowserToggle,
  onLocalToggle,
  onTypedSubmit,
  processing,
  recording,
  setTypedCommand,
  state,
  textInputEnabled,
  typedCommand,
  vadReady,
  wakeWordEnabled,
  setWakeWordEnabled,
  micEnergyLevel = 0,
}) {
  const useLocalVoice = localVoiceEnabled && localVoiceAvailable;
  const useBrowserVoice = !useLocalVoice && browserFallbackEnabled && browserSpeechSupported;
  const voiceEnabled = micEnabled && (useLocalVoice || useBrowserVoice);
  const active = recording || state === "listening";
  const onClick = useLocalVoice ? onLocalToggle : onBrowserToggle;

  return (
    <div className="relative z-30 flex flex-col items-center gap-3 sm:gap-4">
      {/* VAD status badge */}
      {useLocalVoice && vadReady && (
        <div
          title="Silero VAD active — auto end-of-speech detection enabled"
          className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[9px] font-mono tracking-widest uppercase bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
        >
          <Activity size={10} className="animate-pulse" />
          VAD ACTIVE
        </div>
      )}

      {/* Center Mic Button with Sonar Rings and Spinner */}
      <div className="relative flex items-center justify-center">
        {/* Sonar Ripple Rings */}
        {active && [1, 2, 3].map((ring) => (
          <Motion.div
            key={ring}
            className="absolute rounded-full border pointer-events-none w-20 h-20"
            style={{ borderColor: "var(--th-primary)" }}
            animate={{
              scale: [1, 1.35 + ring * 0.3 + micEnergyLevel * 0.5],
              opacity: [0.6 - ring * 0.15, 0],
            }}
            transition={{
              duration: 1.8,
              repeat: Infinity,
              delay: (ring - 1) * 0.5,
              ease: "easeOut",
            }}
          />
        ))}

        {/* Processing Spinner Ring */}
        {processing && (
          <Motion.div
            className="absolute w-24 h-24 rounded-full border-t-2 pointer-events-none"
            style={{ borderColor: "var(--th-primary)" }}
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          />
        )}

        {/* Tactical Mic Button */}
        <button
          onClick={voiceEnabled ? onClick : undefined}
          aria-label={active ? "Stop listening" : "Start listening"}
          disabled={!voiceEnabled || processing}
          className="relative w-20 h-20 rounded-full flex items-center justify-center backdrop-blur-md transition-transform duration-200 active:scale-95 disabled:opacity-40"
          style={{
            background: active ? "var(--th-primary-glow)" : "rgba(10, 14, 23, 0.85)",
            border: "1px solid var(--th-border)",
            boxShadow: active ? "0 0 25px var(--th-primary-glow)" : "none",
          }}
        >
          {processing ? (
            <RefreshCw className="w-8 h-8 animate-spin" style={{ color: "var(--th-primary)" }} />
          ) : active ? (
            <Mic className="w-8 h-8" style={{ color: "var(--th-primary)" }} />
          ) : !voiceEnabled ? (
            <MicOff className="w-8 h-8 text-neutral-500" />
          ) : (
            <Mic className="w-8 h-8 text-neutral-300" />
          )}
        </button>
      </div>

      {/* Standby / Wake Active Status Chip */}
      {useBrowserVoice && (
        <button
          onClick={() => setWakeWordEnabled(!wakeWordEnabled)}
          title={wakeWordEnabled ? "Disable wake word" : 'Enable wake word'}
          className="px-3 py-1 rounded border font-mono text-[9px] tracking-widest uppercase transition-all"
          style={{
            borderColor: wakeWordEnabled ? "var(--th-border-bright)" : "var(--th-border)",
            color: wakeWordEnabled ? "var(--th-primary)" : "var(--th-text-dim)",
            background: wakeWordEnabled ? "var(--th-primary-subtle)" : "transparent",
          }}
        >
          {wakeWordEnabled ? "● WAKE ACTIVE" : "○ STANDBY"}
        </button>
      )}

      {!useLocalVoice && !useBrowserVoice && (
        <div className="text-xs text-yellow-300/80 font-mono text-center max-w-xs">
          Speech recognition is not available. Install local voice models, enable browser speech fallback, or use typed input.
        </div>
      )}

      {(textInputEnabled || !voiceEnabled) && (
        <CommandInput
          disabled={processing}
          onSubmit={onTypedSubmit}
          setTypedCommand={setTypedCommand}
          typedCommand={typedCommand}
        />
      )}
    </div>
  );
}
