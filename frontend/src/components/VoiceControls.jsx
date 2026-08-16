import { Activity, Mic, Radio, StopCircle } from "lucide-react";
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
}) {
  const useLocalVoice = localVoiceEnabled && localVoiceAvailable;
  const useBrowserVoice = !useLocalVoice && browserFallbackEnabled && browserSpeechSupported;
  const voiceEnabled = micEnabled && (useLocalVoice || useBrowserVoice);
  const active = recording || state === "listening";
  const onClick = useLocalVoice ? onLocalToggle : onBrowserToggle;

  return (
    <div className="absolute bottom-0 z-50 flex flex-col items-center gap-3 sm:gap-4">
      {useBrowserVoice && (
        <button
          onClick={() => setWakeWordEnabled(!wakeWordEnabled)}
          title={wakeWordEnabled ? "Disable wake word" : 'Enable "Hey Meero" wake word'}
          className={`p-2 rounded-full text-xs ${wakeWordEnabled ? "bg-green-500/80 text-white" : "bg-gray-700/50 text-gray-400"}`}
        >
          <Radio size={18} />
        </button>
      )}
      {/* VAD status badge — shown when local voice is active and model is ready */}
      {useLocalVoice && vadReady && (
        <div
          title="Silero VAD active — auto end-of-speech detection enabled"
          className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-widest bg-emerald-500/20 border border-emerald-400/40 text-emerald-300"
        >
          <Activity size={10} className="animate-pulse" />
          VAD
        </div>
      )}
      <button
        onClick={voiceEnabled ? onClick : undefined}
        aria-label={active ? "Stop listening" : "Start listening"}
        disabled={!voiceEnabled || processing}
        className={`p-6 sm:p-5 rounded-full transition-all ${active ? "bg-red-500/90" : "bg-cyan-600/90"} ${!voiceEnabled ? "opacity-50 cursor-not-allowed" : ""}`}
      >
        {active ? <StopCircle size={32} /> : <Mic size={32} />}
      </button>
      {!useLocalVoice && !useBrowserVoice && (
        <div className="text-xs text-yellow-300 text-center max-w-xs">
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
