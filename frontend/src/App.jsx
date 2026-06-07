import { Settings } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { getModelStatus, sendCommand } from "./api";
import AssistantOrb from "./components/AssistantOrb";
import Background from "./components/Background";
import HistoryPanel from "./components/HistoryPanel";
import HologramOverlay from "./components/HologramOverlay";
import SettingsPanel from "./components/SettingsPanel";
import StatusBanner from "./components/StatusBanner";
import VoiceControls from "./components/VoiceControls";
import useHealthSettings from "./hooks/useHealthSettings";
import useMessages from "./hooks/useMessages";
import useSpeechRecognition from "./hooks/useSpeechRecognition";
import useSpeechSynthesis from "./hooks/useSpeechSynthesis";
import useVoicePipeline from "./hooks/useVoicePipeline";
import "./index.css";
import { playProcessing, playStartup } from "./utils/sound";
import { browserSpeechRecognitionSupported } from "./utils/speechSupport";

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
  const [loadingText, setLoadingText] = useState("INITIALIZING SYSTEM CORE...");
  const [serverReachable, setServerReachable] = useState(true);
  const [ggufMissing, setGgufMissing] = useState(false);
  const [modelStatus, setModelStatus] = useState(null);

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
    return () => {
      window.removeEventListener("click", handleFirstClick);
    };
  }, []);

  useEffect(() => {
    let polling = true;
    
    const checkStatus = async () => {
      const status = await getModelStatus();
      if (!polling) return;

      if (!status) {
        // If API fails, just retry next cycle
        return;
      }
      setModelStatus(status);
      
      const nnLoaded = !status.neural_net?.enabled || status.neural_net?.loaded;
      const ggufLoaded = !status.gguf_llm?.enabled || status.gguf_llm?.loaded;

      if (status.gguf_llm?.status === "missing") {
        setGgufMissing(true);
      }

      if (!nnLoaded && !ggufLoaded) {
        setLoadingText("LOADING NEURAL NET & GGUF MODEL...");
      } else if (!nnLoaded) {
        setLoadingText("LOADING NEURAL NET...");
      } else if (!ggufLoaded) {
        if (status.gguf_llm?.status === "missing") {
          setLoadingText("GGUF MODEL MISSING...");
        } else {
          setLoadingText("LOADING GGUF MODEL...");
        }
      }

      // If missing GGUF, we stay on boot screen until user decides to bypass.
      // The bypass sets ggufLoaded artificially or disables it.
      if (nnLoaded && ggufLoaded) {
        setBooting(false);
      }
    };

    // Initial check
    checkStatus();

    // Poll every 2 seconds
    const interval = setInterval(checkStatus, 2000);

    return () => {
      polling = false;
      clearInterval(interval);
    };
  }, []);

  // -- SPEECH HOOKS --
  // Refs to break circular dependency: handleCommand → speak → recognition
  const speakRef = useRef(null);
  const cancelSpeechRef = useRef(null);
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
    () => cancelSpeechRef.current && cancelSpeechRef.current()
  );

  // Feature-detect Web Speech API availability so we can give feedback
  const speechSupported = browserSpeechRecognitionSupported();

  const {
    apiHealth,
    lastHealthCheckedAt,
    refreshHealth,
    saveAssistantSettings,
    voicePitch,
    setVoicePitch,
    voiceRate,
    setVoiceRate,
    micEnabled,
    setMicEnabled,
    textOutputEnabled,
    setTextOutputEnabled,
    showHistory,
    setShowHistory,
    textInputEnabled,
    setTextInputEnabled,
    localVoiceEnabled,
    setLocalVoiceEnabled,
    browserSpeechFallbackEnabled,
    setBrowserSpeechFallbackEnabled,
  } = useHealthSettings({ wakeWordEnabled, setWakeWordEnabled });

  useEffect(() => {
    const handler = (e) => {
      try { setServerReachable(Boolean(e.detail?.reachable)); } catch { setServerReachable(false); }
    };
    window.addEventListener('meero:server-reachable', handler);
    return () => window.removeEventListener('meero:server-reachable', handler);
  }, []);

  const tryReconnect = useCallback(async () => {
    // Trigger a health refresh which will also emit reachable events
    try { await refreshHealth(); } catch { /* ignore */ }
  }, [refreshHealth]);

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

  const { speak, cancel: cancelSpeech } = useSpeechSynthesis(
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
    const yesWords = new Set(["yes", "y", "yeah", "yep", "ok", "okay", "confirm", "proceed", "do it"]);
    const noWords = new Set(["no", "n", "nope", "cancel", "stop", "don't", "do not"]);

    if (pendingConfirmationCommand) {
      if (yesWords.has(normalized)) {
        setState("processing");
        playProcessing();
        const confirmedCommand = pendingConfirmationCommand;
        const confirmData = await sendCommand(pendingConfirmationCommand, {
          confirm: true,
          pendingCommand: pendingConfirmationCommand,
        });
        setPendingConfirmationCommand(null);
        if (confirmData.sentiment) setSentiment(confirmData.sentiment);
        if (["blocked", "error", "rate_limited"].includes(confirmData.action_status)) {
          setStatusNotice(confirmData.response);
        }
        if (textOutputEnabled) {
          addMessages([
            { role: "user", text: normalized },
            { role: "assistant", text: confirmData.response },
          ]);
        } else {
          addMessages([{ role: "user", text: normalized }]);
        }
        setStatusNotice(confirmedCommand ? "Action confirmed." : "");
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
    if (textOutputEnabled) {
      addMessages([
        { role: "user", text: userText },
        { role: "assistant", text: data.response },
      ]);
    } else {
      addMessages([{ role: "user", text: userText }]);
    }
    speakRef.current(data.response);
  }, [addMessages, pendingConfirmationCommand, textOutputEnabled]);

  const handleLocalVoiceResult = useCallback(async (data) => {
    if (data.action_status === "confirmation_required" && data.pending_command) {
      setPendingConfirmationCommand(data.pending_command);
    } else if (data.action_status !== "confirmation_required") {
      setPendingConfirmationCommand(null);
    }
    if (data.sentiment) setSentiment(data.sentiment);
    if (["blocked", "error", "rate_limited", "cancelled"].includes(data.action_status)) {
      setStatusNotice(data.response);
    }
    const nextMessages = [{ role: "user", text: data.transcript || "Voice command" }];
    if (textOutputEnabled) nextMessages.push({ role: "assistant", text: data.response });
    addMessages(nextMessages);
    setState("idle");
  }, [addMessages, textOutputEnabled]);

  const {
    recording: localRecording,
    processing: localVoiceProcessing,
    error: localVoiceError,
    supported: localCaptureSupported,
    toggleRecording: toggleLocalRecording,
  } = useVoicePipeline({
    onResult: handleLocalVoiceResult,
    pendingCommand: pendingConfirmationCommand,
  });
  const localVoiceAvailable = Boolean(
    localVoiceEnabled && modelStatus?.voice?.stt?.available && localCaptureSupported,
  );

  useEffect(() => {
    const browserVoiceActive = !localVoiceAvailable && browserSpeechFallbackEnabled;
    if (!browserVoiceActive && wakeWordEnabled) setWakeWordEnabled(false);
  }, [browserSpeechFallbackEnabled, localVoiceAvailable, setWakeWordEnabled, wakeWordEnabled]);

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
    cancelSpeechRef.current = cancelSpeech;
    handleCommandRef.current = handleCommand;
  }, [speak, cancelSpeech, handleCommand]);

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
          {loadingText}
        </div>
        {ggufMissing && (
          <div className="mt-8 flex flex-col items-center gap-4 animate-in fade-in zoom-in duration-500">
            <div className="text-red-500 text-sm tracking-widest">
              GGUF Model file could not be found locally.
            </div>
            <button
              onClick={() => {
                setGgufMissing(false);
                setBooting(false);
              }}
              className="px-6 py-2 border-2 border-red-500 text-red-500 hover:bg-red-500 hover:text-black transition-colors uppercase tracking-widest font-bold"
            >
              Continue without LLM
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="min-h-screen text-white font-sans overflow-hidden flex flex-col items-center justify-center p-4 relative">
      {/* Screen-reader live region for TTS responses */}
      <div aria-live="polite" className="sr-only" data-testid="aria-response">{ariaResponse}</div>
      <Background />
      <HologramOverlay />

      {!serverReachable && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-60 rounded bg-red-700/90 px-4 py-2 text-sm text-white shadow">
          Server unreachable - <button onClick={tryReconnect} className="underline">Retry</button>
        </div>
      )}
      {serverReachable && (statusNotice || recognitionError || localVoiceError) && (
        <StatusBanner
          serverReachable={serverReachable}
          notice={statusNotice || recognitionError || localVoiceError}
          onRetry={tryReconnect}
        />
      )}

      {showHistory && (
        <HistoryPanel messages={messages} onClear={clearMessages} onCopy={copyMessage} />
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
        <SettingsPanel
          apiHealth={apiHealth}
          lastHealthCheckedAt={lastHealthCheckedAt}
          onClose={() => setSettingsOpen(false)}
          onRefreshHealth={refreshHealth}
          onSave={handleSettingsSave}
          setVoicePitch={setVoicePitch}
          setVoiceRate={setVoiceRate}
          setWakeWordEnabled={setWakeWordEnabled}
          setMicEnabled={setMicEnabled}
          setTextOutputEnabled={setTextOutputEnabled}
          setShowHistory={setShowHistory}
          setTextInputEnabled={setTextInputEnabled}
          voicePitch={voicePitch}
          voiceRate={voiceRate}
          wakeWordEnabled={wakeWordEnabled}
          micEnabled={micEnabled}
          textOutputEnabled={textOutputEnabled}
          showHistory={showHistory}
          textInputEnabled={textInputEnabled}
          localVoiceEnabled={localVoiceEnabled}
          browserSpeechFallbackEnabled={browserSpeechFallbackEnabled}
          setLocalVoiceEnabled={setLocalVoiceEnabled}
          setBrowserSpeechFallbackEnabled={setBrowserSpeechFallbackEnabled}
        />
      )}

      {/* Tactical Center */}
      <div className="w-full max-w-lg h-auto aspect-square flex flex-col items-center justify-center p-8 relative z-10">
        {/* Header */}
        <div className="text-center z-30 mb-4 transform translate-y-4">
          <h1 className="text-2xl font-orbitron font-bold tracking-[0.2em] text-cyan-400 drop-shadow-[0_0_10px_rgba(34,211,238,0.5)]">
            MEERO
          </h1>
        </div>

        {/* Visualizer - Center Stage */}
        <div className="flex-1 flex items-center justify-center w-full h-full relative z-20">
          <AssistantOrb state={state} sentiment={sentiment} />
        </div>

        <VoiceControls
          browserFallbackEnabled={browserSpeechFallbackEnabled}
          browserSpeechSupported={speechSupported}
          localVoiceAvailable={localVoiceAvailable}
          localVoiceEnabled={localVoiceEnabled}
          micEnabled={micEnabled}
          onBrowserToggle={toggleListen}
          onLocalToggle={toggleLocalRecording}
          onTypedSubmit={handleTypedSubmit}
          processing={state === "processing" || localVoiceProcessing}
          recording={localRecording}
          setTypedCommand={setTypedCommand}
          state={state}
          textInputEnabled={textInputEnabled}
          typedCommand={typedCommand}
          wakeWordEnabled={wakeWordEnabled}
          setWakeWordEnabled={setWakeWordEnabled}
        />
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
