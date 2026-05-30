import { Mic, Radio, Settings, StopCircle } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { sendCommand } from "./api";
import Background from "./components/Background";
import CommandInput from "./components/CommandInput";
import HistoryPanel from "./components/HistoryPanel";
import HologramOverlay from "./components/HologramOverlay";
import SettingsPanel from "./components/SettingsPanel";
import ThreeOrb from "./components/ThreeOrb";
import useHealthSettings from "./hooks/useHealthSettings";
import useMessages from "./hooks/useMessages";
import useSpeechRecognition from "./hooks/useSpeechRecognition";
import useSpeechSynthesis from "./hooks/useSpeechSynthesis";
import "./index.css";
import { playProcessing, playStartup } from "./utils/sound";

function App() {
  const [state, setState] = useState("idle"); // idle, listening, processing, speaking
  const [sentiment, setSentiment] = useState("neutral"); // neutral, positive, negative
  const [pendingConfirmationCommand, setPendingConfirmationCommand] = useState(null);
  const [typedCommand, setTypedCommand] = useState("");
  const [statusNotice, setStatusNotice] = useState("");
  const { messages, addMessages, clearMessages } = useMessages();
  const [settingsOpen, setSettingsOpen] = useState(false);

  // -- BOOT SEQUENCE STATE --
  const [booting, setBooting] = useState(true);

  // Startup Sound
  useEffect(() => {
    const storage = typeof window !== "undefined" ? window.localStorage : null;
    const hasInteracted = storage?.getItem?.("hasInteracted");
    const handleFirstClick = () => {
      playStartup();
      storage?.setItem?.("hasInteracted", "true");
      window.removeEventListener("click", handleFirstClick);
    };

    // Web Audio API requires user interaction to start
    if (!hasInteracted) {
      window.addEventListener("click", handleFirstClick);
    }
  }, []);

  useEffect(() => {
    // Fake boot sequence
    const timer = setTimeout(() => {
      setBooting(false);
    }, 3500); // 3.5s boot time
    return () => clearTimeout(timer);
  }, []);

  // -- SPEECH HOOKS --
  // Refs to break circular dependency: handleCommand → speak → recognition
  const speakRef = useRef(null);
  const handleCommandRef = useRef(null);

  const {
    isConversing,
    isConversingRef,
    toggleListen,
    recognitionRef,
    wakeWordEnabled,
    setWakeWordEnabled,
    startActiveListening,
    recognitionError,
  } = useSpeechRecognition(
    (text) => handleCommandRef.current(text),
    state,
    setState,
  );

  // Feature-detect Web Speech API availability so we can give feedback
  const speechSupported = typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);

  const {
    apiHealth,
    lastHealthCheckedAt,
    refreshHealth,
    saveAssistantSettings,
    voicePitch,
    setVoicePitch,
    voiceRate,
    setVoiceRate,
  } = useHealthSettings({ wakeWordEnabled, setWakeWordEnabled });

  const copyMessage = useCallback(async (text) => {
    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error("Clipboard unavailable");
      }
      await navigator.clipboard?.writeText(text);
      setStatusNotice("Copied response.");
    } catch {
      setStatusNotice("Could not copy response.");
    }
  }, []);

  const { speak } = useSpeechSynthesis(
    setState,
    useCallback(() => {
      // Determine what to do after speaking
      if (isConversingRef.current) {
        // Manual mode: plain restart
        setTimeout(() => {
          try {
            recognitionRef.current.start();
          } catch {
            /* */
          }
        }, 150);
      } else if (wakeWordEnabled) {
        // Wake word mode: Continued Conversation (active listening)
        startActiveListening();
      }
    }, [
      wakeWordEnabled,
      startActiveListening,
      isConversingRef,
      recognitionRef,
    ]),
    { rate: voiceRate, pitch: voicePitch },
  );

  const handleCommand = useCallback(async (text) => {
    if (!text.trim()) return;
    setStatusNotice("");
    const userText = text.trim();

    const normalized = userText.toLowerCase();
    const yesWords = new Set(["yes", "y", "ok", "okay", "confirm", "proceed", "do it"]);
    const noWords = new Set(["no", "n", "cancel", "stop", "don't", "do not"]);

    if (pendingConfirmationCommand) {
      if (yesWords.has(normalized)) {
        setState("processing");
        playProcessing();
        const confirmData = await sendCommand(pendingConfirmationCommand, {
          confirm: true,
          pendingCommand: pendingConfirmationCommand,
        });
        setPendingConfirmationCommand(null);
        if (confirmData.sentiment) setSentiment(confirmData.sentiment);
        if (["blocked", "error", "rate_limited"].includes(confirmData.action_status)) {
          setStatusNotice(confirmData.response);
        }
        addMessages([
          { role: "user", text: normalized },
          { role: "assistant", text: confirmData.response },
        ]);
        speakRef.current(confirmData.response);
        return;
      }

      if (noWords.has(normalized)) {
        setPendingConfirmationCommand(null);
        setStatusNotice("Action cancelled.");
        speakRef.current("Action cancelled.");
        return;
      }

      setStatusNotice("Please answer yes or no.");
      speakRef.current("Please say yes to continue or no to cancel.");
      return;
    }

    setState("processing");
    playProcessing();

    const data = await sendCommand(userText);
    if (data.action_status === "confirmation_required" && data.pending_command) {
      setPendingConfirmationCommand(data.pending_command);
    }
    if (data.sentiment) setSentiment(data.sentiment);
    if (["blocked", "error", "rate_limited"].includes(data.action_status)) {
      setStatusNotice(data.response);
    }
    addMessages([
      { role: "user", text: userText },
      { role: "assistant", text: data.response },
    ]);
    speakRef.current(data.response);
  }, [addMessages, pendingConfirmationCommand]);

  const handleTypedSubmit = useCallback((event) => {
    event.preventDefault();
    const command = typedCommand.trim();
    if (!command) return;
    setTypedCommand("");
    handleCommand(command);
  }, [typedCommand, handleCommand]);

  // Keep refs in sync (must be in effect, not during render)
  const [ariaResponse, setAriaResponse] = useState("");

  useEffect(() => {
    // Wrap speak to also update an aria-live region for screen readers
    speakRef.current = (text) => {
      try {
        setAriaResponse(text);
      } catch {
        // Ignore aria-live update failures.
      }
      speak(text);
    };
    handleCommandRef.current = handleCommand;
  }, [speak, handleCommand]);

  const handleSettingsSave = useCallback(async () => {
    const result = await saveAssistantSettings();
    setStatusNotice(result.status === "ok" ? "Settings saved." : "Could not save settings.");
  }, [saveAssistantSettings]);

  if (booting) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-black text-white font-orbitron overflow-hidden">
        <div className="text-4xl font-bold tracking-[0.5em] text-cyan-500 animate-pulse border-b-2 border-cyan-500 pb-2 mb-4">
          MEERO
        </div>
        <div className="font-rajdhani text-sm text-cyan-800 tracking-widest mt-2 animate-bounce">
          INITIALIZING SYSTEM CORE...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen text-white font-sans overflow-hidden flex flex-col items-center justify-center p-4 relative">
      {/* Screen-reader live region for TTS responses */}
      <div aria-live="polite" className="sr-only" data-testid="aria-response">{ariaResponse}</div>
      <Background />
      <HologramOverlay />

      <HistoryPanel messages={messages} onClear={clearMessages} onCopy={copyMessage} />

      <button
        onClick={() => setSettingsOpen(true)}
        aria-label="Open settings"
        title="Open settings"
        className="absolute right-4 top-4 z-50 grid h-10 w-10 place-items-center rounded-full border border-cyan-400/25 bg-black/45 text-cyan-100 backdrop-blur transition hover:bg-cyan-900/40"
      >
        <Settings size={18} />
      </button>

      {settingsOpen && (
        <SettingsPanel
          apiHealth={apiHealth}
          lastHealthCheckedAt={lastHealthCheckedAt}
          onClose={() => setSettingsOpen(false)}
          onRefreshHealth={refreshHealth}
          onSave={handleSettingsSave}
          setVoicePitch={setVoicePitch}
          setVoiceRate={setVoiceRate}
          setWakeWordEnabled={setWakeWordEnabled}
          voicePitch={voicePitch}
          voiceRate={voiceRate}
          wakeWordEnabled={wakeWordEnabled}
        />
      )}

      {/* Tactical Center */}
      <div className="w-full max-w-sm h-auto aspect-square flex flex-col items-center justify-center p-8 relative z-10">
        {/* Header */}
        <div className="text-center z-30 mb-4 transform translate-y-4">
          <h1 className="text-2xl font-orbitron font-bold tracking-[0.2em] text-cyan-400 drop-shadow-[0_0_10px_rgba(34,211,238,0.5)]">
            MEERO
          </h1>
        </div>

        {/* Visualizer - Center Stage */}
        <div className="flex-1 flex items-center justify-center w-full h-full relative z-20">
          <ThreeOrb state={state} sentiment={sentiment} />
        </div>

        {/* Controls - Bottom */}
        <div className="absolute bottom-0 z-50 flex flex-col items-center gap-3">
          {/* Wake Word Toggle */}
          <button
            onClick={() => setWakeWordEnabled(!wakeWordEnabled)}
            title={
              wakeWordEnabled
                ? "Disable wake word"
                : 'Enable "Hey Meero" wake word'
            }
            className={`p-2 rounded-full transition-all duration-300 text-xs ${
              wakeWordEnabled
                ? "bg-green-500/80 shadow-[0_0_20px_rgba(34,197,94,0.4)] text-white"
                : "bg-gray-700/50 hover:bg-gray-600 text-gray-400"
            }`}
          >
            <Radio size={18} />
          </button>

          {/* Mic Button */}
          <button
            onClick={speechSupported ? toggleListen : undefined}
            aria-label={
              state === "listening" ? "Stop listening" : "Start listening"
            }
            aria-disabled={!speechSupported}
            title={!speechSupported ? "Speech recognition unavailable in this browser. Use Chrome or enable Web Speech API." : undefined}
            disabled={!speechSupported}
            className={`p-6 rounded-full transition-all duration-300 transform hover:scale-105 active:scale-95 ${
              state === "listening"
                ? "bg-red-500/90 shadow-[0_0_40px_rgba(239,68,68,0.6)] animate-pulse"
                : "bg-cyan-600/90 hover:bg-cyan-500 shadow-[0_0_30px_rgba(8,145,178,0.4)]"
            } ${!speechSupported ? "opacity-50 cursor-not-allowed" : ""}`}
          >
            {state === "listening" ? (
              <StopCircle size={32} />
            ) : (
              <Mic size={32} />
            )}
          </button>
          {!speechSupported && (
            <div className="text-xs text-yellow-300 mt-2 text-center max-w-xs z-50">
              Speech recognition is not available in this browser. Try Chrome or Edge and enable microphone permissions.
            </div>
          )}
          <CommandInput
            disabled={state === "processing"}
            onSubmit={handleTypedSubmit}
            setTypedCommand={setTypedCommand}
            typedCommand={typedCommand}
          />
          {(statusNotice || recognitionError) && (
            <div className="text-xs text-yellow-200 text-center max-w-xs z-50">
              {statusNotice || recognitionError}
            </div>
          )}
        </div>
      </div>

      {/* Minimal State Indicator */}
      <div className="absolute bottom-10 flex flex-col items-center gap-1 text-xs text-gray-500 tracking-widest uppercase opacity-50">
        <span>{wakeWordEnabled ? "wake word active" : `${state} Mode`}</span>
        {isConversing && (
          <span className="text-cyan-500 animate-pulse">● Continuous Loop</span>
        )}
        {wakeWordEnabled && (
          <span className="text-green-400 animate-pulse">
            ● Listening for "Hey Meero"
          </span>
        )}
      </div>
    </div>
  );
}

export default App;
