import { Copy, Mic, Radio, RefreshCw, Send, Settings, StopCircle, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { getHealth, getSettings, saveSettings, sendCommand } from "./api";
import Background from "./components/Background";
import HologramOverlay from "./components/HologramOverlay";
import ThreeOrb from "./components/ThreeOrb";
import useSpeechRecognition from "./hooks/useSpeechRecognition";
import useSpeechSynthesis from "./hooks/useSpeechSynthesis";
import "./index.css";
import { playProcessing, playStartup } from "./utils/sound";

const MAX_STORED_MESSAGES = 25;

const loadStoredMessages = () => {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage?.getItem?.("meero.messages");
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((message) => message?.role && typeof message.text === "string")
      .slice(-MAX_STORED_MESSAGES);
  } catch {
    return [];
  }
};

const formatMessageTime = (createdAt) => {
  if (!createdAt) return "";
  const date = new Date(createdAt);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
};

function App() {
  const [state, setState] = useState("idle"); // idle, listening, processing, speaking
  const [sentiment, setSentiment] = useState("neutral"); // neutral, positive, negative
  const [pendingConfirmationCommand, setPendingConfirmationCommand] = useState(null);
  const [typedCommand, setTypedCommand] = useState("");
  const [statusNotice, setStatusNotice] = useState("");
  const [messages, setMessages] = useState(loadStoredMessages);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [voiceRate, setVoiceRate] = useState(1);
  const [voicePitch, setVoicePitch] = useState(1);
  const [apiHealth, setApiHealth] = useState(null);
  const [lastHealthCheckedAt, setLastHealthCheckedAt] = useState(null);

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

  const addMessages = useCallback((nextMessages) => {
    const createdAt = new Date().toISOString();
    setMessages((prev) => [
      ...prev,
      ...nextMessages.map((message) => ({
        ...message,
        createdAt: message.createdAt || createdAt,
      })),
    ].slice(-MAX_STORED_MESSAGES));
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

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

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      if (messages.length > 0) {
        window.localStorage?.setItem?.("meero.messages", JSON.stringify(messages));
      } else {
        window.localStorage?.removeItem?.("meero.messages");
      }
    } catch {
      /* Ignore storage errors. */
    }
  }, [messages]);

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

  const refreshHealth = useCallback(async () => {
    const health = await getHealth();
    setApiHealth(health);
    setLastHealthCheckedAt(new Date().toISOString());
    return health;
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loadStatus = async () => {
      const [health, settings] = await Promise.all([getHealth(), getSettings()]);
      if (cancelled) return;
      setApiHealth(health);
      setLastHealthCheckedAt(new Date().toISOString());
      if (typeof settings.wake_word_enabled === "boolean") {
        setWakeWordEnabled(settings.wake_word_enabled);
      }
      if (typeof settings.voice_rate === "number") setVoiceRate(settings.voice_rate);
      if (typeof settings.voice_pitch === "number") setVoicePitch(settings.voice_pitch);
    };
    loadStatus();
    return () => {
      cancelled = true;
    };
  }, [setWakeWordEnabled]);

  const handleSettingsSave = useCallback(async () => {
    const result = await saveSettings({
      wake_word_enabled: wakeWordEnabled,
      voice_rate: voiceRate,
      voice_pitch: voicePitch,
    });
    setStatusNotice(result.status === "ok" ? "Settings saved." : "Could not save settings.");
  }, [wakeWordEnabled, voiceRate, voicePitch]);

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

      {messages.length > 0 && (
        <div className="absolute left-4 top-4 z-40 w-[min(20rem,calc(100vw-2rem))] max-h-64 overflow-y-auto rounded border border-cyan-400/20 bg-black/40 p-3 text-xs text-cyan-50/85 backdrop-blur">
          <div className="mb-3 flex items-center justify-between border-b border-cyan-400/10 pb-2">
            <span className="font-orbitron text-[0.65rem] uppercase tracking-widest text-cyan-300">History</span>
            <button
              type="button"
              onClick={clearMessages}
              aria-label="Clear conversation history"
              title="Clear conversation history"
              className="grid h-7 w-7 place-items-center rounded-full text-cyan-100 transition hover:bg-cyan-900/40"
            >
              <Trash2 size={13} />
            </button>
          </div>
          {messages.map((msg, index) => (
            <div key={`${msg.role}-${index}`} className="mb-2 flex items-start gap-2 last:mb-0">
              <div className="min-w-0 flex-1">
                <div className="mb-0.5 flex items-center gap-2">
                  <span className="text-cyan-300">{msg.role}:</span>
                  {formatMessageTime(msg.createdAt) && (
                    <time className="text-[0.65rem] text-cyan-100/45">{formatMessageTime(msg.createdAt)}</time>
                  )}
                </div>
                <span className="break-words">{msg.text}</span>
              </div>
              {msg.role === "assistant" && (
                <button
                  type="button"
                  onClick={() => copyMessage(msg.text)}
                  aria-label={`Copy assistant response ${index + 1}`}
                  title="Copy response"
                  className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full text-cyan-100 transition hover:bg-cyan-900/40"
                >
                  <Copy size={12} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      <button
        onClick={() => setSettingsOpen(true)}
        aria-label="Open settings"
        title="Open settings"
        className="absolute right-4 top-4 z-50 grid h-10 w-10 place-items-center rounded-full border border-cyan-400/25 bg-black/45 text-cyan-100 backdrop-blur transition hover:bg-cyan-900/40"
      >
        <Settings size={18} />
      </button>

      {settingsOpen && (
        <div className="absolute right-4 top-16 z-50 w-[min(21rem,calc(100vw-2rem))] rounded border border-cyan-400/25 bg-black/75 p-4 text-sm text-cyan-50 shadow-[0_0_32px_rgba(8,145,178,0.22)] backdrop-blur">
          <div className="mb-4 flex items-center justify-between">
            <span className="font-orbitron text-xs uppercase tracking-widest text-cyan-300">Settings</span>
            <button
              onClick={() => setSettingsOpen(false)}
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
              onClick={refreshHealth}
              aria-label="Refresh API status"
              title="Refresh API status"
              className="grid h-7 place-items-center rounded border border-cyan-400/20 text-cyan-100 transition hover:bg-cyan-900/40"
            >
              <RefreshCw size={13} />
            </button>
          </div>

          <button
            onClick={handleSettingsSave}
            className="w-full rounded bg-cyan-600/90 px-3 py-2 text-sm text-white transition hover:bg-cyan-500"
          >
            Save
          </button>
        </div>
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
          <form
            onSubmit={handleTypedSubmit}
            className="flex items-center gap-2 w-[min(20rem,80vw)] rounded-full bg-black/45 border border-cyan-400/25 px-3 py-2 shadow-[0_0_24px_rgba(8,145,178,0.16)] backdrop-blur"
          >
            <input
              value={typedCommand}
              onChange={(event) => setTypedCommand(event.target.value)}
              aria-label="Type command"
              placeholder="Type a command"
              disabled={state === "processing"}
              className="min-w-0 flex-1 bg-transparent text-sm text-cyan-50 placeholder:text-cyan-200/40 outline-none"
            />
            <button
              type="submit"
              aria-label="Send command"
              disabled={!typedCommand.trim() || state === "processing"}
              className="grid h-8 w-8 place-items-center rounded-full bg-cyan-600/90 text-white transition hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Send size={16} />
            </button>
          </form>
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
