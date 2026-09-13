import { AnimatePresence } from "framer-motion";
import { MessagesSquare, Settings } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { getModelStatus, sendCommand } from "./api";
import AssistantOrb from "./components/AssistantOrb";
import Background from "./components/Background";
import ConfirmationCard from "./components/ConfirmationCard";
import ErrorBoundary from "./components/ErrorBoundary";
import HistoryPanel from "./components/HistoryPanel";
import HologramOverlay from "./components/HologramOverlay";
import SettingsPanel from "./components/SettingsPanel";
import StatusBanner from "./components/StatusBanner";
import VoiceControls from "./components/VoiceControls";
import useHealthSettings from "./hooks/useHealthSettings";
import useMessages from "./hooks/useMessages";
import useSpeechRecognition from "./hooks/useSpeechRecognition";
import useSpeechSynthesis from "./hooks/useSpeechSynthesis";
import { useTheme } from "./hooks/useTheme";
import useVoicePipeline from "./hooks/useVoicePipeline";
import "./index.css";
import {
  playConfirmationRequired,
  playError,
  playProcessing,
  playStartup,
  playSuccess,
} from "./utils/sound";
import { browserSpeechRecognitionSupported } from "./utils/speechSupport";

function App() {
  const { theme } = useTheme();
  const [state, setState] = useState("idle"); // idle, listening, processing, speaking
  const [sentiment, setSentiment] = useState("neutral"); // neutral, positive, negative
  const [pendingConfirmationCommand, setPendingConfirmationCommand] = useState(null);
  const [confirmationSubmitting, setConfirmationSubmitting] = useState(false);
  const [typedCommand, setTypedCommand] = useState("");
  const [statusNotice, setStatusNotice] = useState("");
  const [lastMetadata, setLastMetadata] = useState(null);
  const statusNoticeTimerRef = useRef(null);
  const { messages, addMessages, clearMessages } = useMessages();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [historyMobileOpen, setHistoryMobileOpen] = useState(false);

  // -- BOOT SEQUENCE STATE --
  const [booting, setBooting] = useState(true);
  const [bootError, setBootError] = useState(false);
  const [bootRetryKey, setBootRetryKey] = useState(0);
  const [loadingText, setLoadingText] = useState("INITIALIZING SYSTEM CORE...");
  const [serverReachable, setServerReachable] = useState(true);
  const [ggufMissing, setGgufMissing] = useState(false);
  const [modelStatus, setModelStatus] = useState(null);
  const bootPollingPausedRef = useRef(false);

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
    let failedChecks = 0;
    bootPollingPausedRef.current = false;
    
    let interval = null;
    const checkStatus = async () => {
      if (!polling || bootPollingPausedRef.current) return;
      const status = await getModelStatus();
      if (!polling) return;

      if (!status) {
        failedChecks += 1;
        if (failedChecks >= 3) {
          setBootError(true);
          bootPollingPausedRef.current = true;
          if (interval) clearInterval(interval);
        }
        return;
      }
      failedChecks = 0;
      bootPollingPausedRef.current = false;
      setBootError(false);
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
        polling = false;
        if (interval) clearInterval(interval);
      }
    };

    // Initial check
    checkStatus();

    // Poll every 2 seconds during boot only
    interval = setInterval(checkStatus, 2000);

    return () => {
      polling = false;
      if (interval) clearInterval(interval);
    };
  }, [bootRetryKey]);

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

  const showTransientStatusNotice = useCallback((message) => {
    clearTimeout(statusNoticeTimerRef.current);
    setStatusNotice(message);
    if (!message) return;
    statusNoticeTimerRef.current = setTimeout(() => {
      setStatusNotice("");
    }, 5000);
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
    localVoiceEnabled,
  );

  const handleCommand = useCallback(async (text, options = null) => {
    if (!text.trim()) return;
    setStatusNotice("");
    const userText = text.trim();

    const normalized = userText.toLowerCase();
    const yesWords = new Set(["yes", "y", "yeah", "yep", "ok", "okay", "confirm", "proceed", "do it"]);
    const noWords = new Set(["no", "n", "nope", "cancel", "stop", "don't", "do not"]);

    if (pendingConfirmationCommand) {
      if (yesWords.has(normalized)) {
        if (confirmationSubmitting) return;
        setConfirmationSubmitting(true);
        setState("processing");
        playProcessing();
        const confirmPayload = {
          confirm: true,
          pendingCommand: pendingConfirmationCommand,
        };
        if (options && options.mode) confirmPayload.mode = options.mode;
        const confirmData = await sendCommand(pendingConfirmationCommand, confirmPayload);
        setConfirmationSubmitting(false);
        setPendingConfirmationCommand(null);
        if (confirmData.sentiment) setSentiment(confirmData.sentiment);
        if (["blocked", "error", "rate_limited"].includes(confirmData.action_status)) {
          setStatusNotice(confirmData.response);
        } else {
          showTransientStatusNotice("Action confirmed.");
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

    const data = options ? await sendCommand(userText, options) : await sendCommand(userText);
    if (data.metadata) setLastMetadata(data.metadata);
    if (data.action_status === "confirmation_required" && data.pending_command) {
      setPendingConfirmationCommand(data.pending_command);
      playConfirmationRequired();
    } else if (["blocked", "error", "rate_limited"].includes(data.action_status)) {
      playError();
      setStatusNotice(data.response);
    } else {
      playSuccess();
    }
    if (data.sentiment) setSentiment(data.sentiment);
    addMessages([
      { role: "user", text: userText },
      { role: "assistant", text: data.response },
    ]);
    speakRef.current(data.response);
  }, [addMessages, confirmationSubmitting, pendingConfirmationCommand, showTransientStatusNotice]);

  const handleLocalVoiceResult = useCallback(async (data) => {
    if (data.metadata) setLastMetadata(data.metadata);
    if (data.action_status === "confirmation_required" && data.pending_command) {
      setPendingConfirmationCommand(data.pending_command);
      playConfirmationRequired();
    } else if (data.action_status !== "confirmation_required") {
      setPendingConfirmationCommand(null);
    }
    if (data.sentiment) setSentiment(data.sentiment);
    if (["blocked", "error", "rate_limited", "cancelled"].includes(data.action_status)) {
      playError();
      setStatusNotice(data.response);
    } else if (data.response) {
      playSuccess();
      showTransientStatusNotice(data.response);
    }
    const nextMessages = [
      { role: "user", text: data.transcript || "Voice command" },
      { role: "assistant", text: data.response },
    ];
    addMessages(nextMessages);
    if (!data.streaming) {
      setState(data.audio_base64 ? "speaking" : "idle");
    }
  }, [addMessages, showTransientStatusNotice]);

  const {
    recording: localRecording,
    processing: localVoiceProcessing,
    error: localVoiceError,
    supported: localCaptureSupported,
    toggleRecording: toggleLocalRecording,
    micEnergyLevel,
    vadReady,
  } = useVoicePipeline({
    onResult: handleLocalVoiceResult,
    pendingCommand: pendingConfirmationCommand,
    setState,
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

  const handleConfirmation = useCallback((confirmed) => {
    handleCommand(confirmed ? "yes" : "no");
  }, [handleCommand]);

  const handleClearMessages = useCallback(() => {
    setHistoryMobileOpen(false);
    clearMessages();
  }, [clearMessages]);

  const handleShowHistoryChange = useCallback((show) => {
    setShowHistory(show);
    if (!show) setHistoryMobileOpen(false);
  }, [setShowHistory]);

  // Keep refs in sync (must be in effect, not during render)
  const [ariaResponse, setAriaResponse] = useState("");

  useEffect(() => {
    // Wrap speak to also update an aria-live region for screen readers
    speakRef.current = (text) => {
      try {
        setAriaResponse(text);
        setTimeout(() => setAriaResponse(""), 150);
      } catch {
        // Ignore aria-live update failures.
      }
      speak(text);
    };
    cancelSpeechRef.current = cancelSpeech;
    handleCommandRef.current = handleCommand;
  }, [speak, cancelSpeech, handleCommand]);

  useEffect(() => {
    return () => clearTimeout(statusNoticeTimerRef.current);
  }, []);

  const handleSettingsSave = useCallback(async (overrides) => {
    const validOverrides =
      overrides && typeof overrides === "object" && !overrides.nativeEvent && !overrides._reactName
        ? overrides
        : {};
    const result = await saveAssistantSettings(validOverrides);
    if (result.status === "ok") {
      showTransientStatusNotice("Settings saved.");
    } else {
      setStatusNotice("Could not save settings.");
    }
  }, [saveAssistantSettings, showTransientStatusNotice]);


  const bootProgress = (() => {
    if (!modelStatus) return 25;
    let score = 25;
    if (modelStatus.neural_net?.loaded) score += 35;
    if (modelStatus.gguf_llm?.loaded || modelStatus.gguf_llm?.status === "missing") score += 40;
    return score;
  })();

  if (booting) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-black text-white font-orbitron overflow-hidden p-6 text-center">
        <div
          className="text-4xl font-bold tracking-[0.4em] animate-pulse border-b-2 pb-2 mb-3"
          style={{
            color: "var(--th-primary)",
            borderColor: "var(--th-primary)",
            textShadow: "0 0 20px var(--th-primary-glow)",
          }}
        >
          {theme.boot?.title || "MEERO"}
        </div>
        <p className="font-mono text-xs tracking-widest text-neutral-400 mb-6 uppercase">
          {theme.boot?.subtitle || "NEURAL DESKTOP ASSISTANT"}
        </p>

        {/* Tactical Boot Progress Bar */}
        <div className="w-64 h-1.5 bg-neutral-900 border border-neutral-800 rounded-full overflow-hidden mb-4">
          <div
            className="h-full transition-all duration-500 rounded-full"
            style={{ width: `${bootProgress}%`, background: "var(--th-primary)" }}
          />
        </div>

        <div
          className="font-mono text-xs tracking-widest uppercase animate-pulse"
          style={{ color: "var(--th-text-dim)" }}
        >
          {loadingText}
        </div>
        {bootError && (
          <div className="mt-8 w-[min(28rem,calc(100vw-2rem))] rounded-2xl border border-red-400/35 bg-red-950/25 p-5 text-center shadow-[0_0_32px_rgba(239,68,68,0.16)]">
            <p className="text-sm font-semibold text-red-300">Meero cannot reach the local server.</p>
            <p className="mt-2 text-xs leading-relaxed" style={{ color: "var(--th-text-dim)" }}>
              You can retry the connection or open the interface in limited mode.
            </p>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setBooting(false)}
                className="rounded-lg border px-3 py-2 text-xs transition hover:brightness-125"
                style={{ borderColor: "var(--th-border)", color: "var(--th-text)" }}
              >
                Limited mode
              </button>
              <button
                type="button"
                onClick={() => {
                  setBootError(false);
                  bootPollingPausedRef.current = false;
                  setLoadingText("RECONNECTING TO LOCAL SERVER...");
                  setBootRetryKey((value) => value + 1);
                }}
                className="rounded-lg px-3 py-2 text-xs font-semibold text-black transition hover:brightness-110 active:scale-95"
                style={{ background: "var(--th-primary)" }}
              >
                Retry connection
              </button>
            </div>
          </div>
        )}
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
      <div aria-live="polite" aria-atomic="true" className="sr-only" data-testid="aria-response">{ariaResponse}</div>
      <Background />
      <HologramOverlay state={state} lastMetadata={lastMetadata} />

      {(!serverReachable || statusNotice || recognitionError || localVoiceError) && (
        <StatusBanner
          serverReachable={serverReachable}
          notice={statusNotice || recognitionError || localVoiceError}
          transient={!recognitionError && !localVoiceError && statusNotice !== "Please answer yes or no."}
          onRetry={tryReconnect}
        />
      )}

      {showHistory && (
        <HistoryPanel
          messages={messages}
          mobileOpen={historyMobileOpen}
          onClear={handleClearMessages}
          onCopy={copyMessage}
          onMobileClose={() => setHistoryMobileOpen(false)}
        />
      )}

      {showHistory && messages.length > 0 && (
        <button
          type="button"
          onClick={() => setHistoryMobileOpen(true)}
          aria-label="Open conversation history"
          title="Open conversation history"
          className="absolute left-4 top-4 z-30 grid h-10 w-10 place-items-center rounded-full border bg-black/45 backdrop-blur transition hover:bg-white/10 md:hidden"
          style={{ borderColor: "var(--th-border)", color: "var(--th-text)" }}
        >
          <MessagesSquare size={18} />
        </button>
      )}

      <button
        onClick={() => setSettingsOpen(true)}
        aria-label="Open settings"
        title="Open settings"
        className="absolute right-4 top-4 z-50 grid h-10 w-10 place-items-center rounded-full border bg-black/45 backdrop-blur transition hover:bg-white/10"
        style={{ borderColor: "var(--th-border)", color: "var(--th-text)" }}
      >
        <Settings size={18} />
      </button>

      <AnimatePresence>
        {settingsOpen && (
          <SettingsPanel
            key="settings-panel"
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
            setShowHistory={handleShowHistoryChange}
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
      </AnimatePresence>


      <ConfirmationCard
        key={pendingConfirmationCommand || "confirmation"}
        command={pendingConfirmationCommand}
        disabled={confirmationSubmitting}
        onCancel={() => handleConfirmation(false)}
        onConfirm={() => handleConfirmation(true)}
        onAnnounce={setAriaResponse}
      />


      {/* Tactical Center */}
      <div className="w-full max-w-lg flex flex-col items-center justify-center min-h-[calc(100dvh-2rem)] md:min-h-0 gap-4 px-4 py-8 pb-[env(safe-area-inset-bottom,1rem)] relative z-10">
        {/* Header */}
        <div className="text-center z-30 mb-2">
          <h1
            className="text-2xl font-orbitron font-bold tracking-[0.2em] transition-colors"
            style={{
              color: "var(--th-primary)",
              textShadow: "0 0 12px var(--th-primary-glow)",
            }}
          >
            {theme.assistantName || "MEERO"}
          </h1>
        </div>

        {/* Visualizer - Center Stage */}
        <div className="flex-1 flex items-center justify-center w-full min-h-[260px] max-h-[440px] relative z-20">
          <ErrorBoundary>
            <AssistantOrb state={state} sentiment={sentiment} micEnergyLevel={micEnergyLevel} />
          </ErrorBoundary>
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
          vadReady={vadReady}
          wakeWordEnabled={wakeWordEnabled}
          setWakeWordEnabled={setWakeWordEnabled}
          micEnergyLevel={micEnergyLevel}
        />
      </div>

      {/* Minimal State Indicator (desktop only to prevent mobile overlay clipping) */}
      <div
        className="hidden md:flex absolute bottom-12 flex-col items-center gap-1 font-mono text-[10px] tracking-widest uppercase transition-colors pointer-events-none z-10"
        style={{ color: "var(--th-text-dim)" }}
      >
        <span>{wakeWordEnabled ? "● WAKE ACTIVE" : `${state.toUpperCase()} MODE`}</span>
        {isConversing && (
          <span className="animate-pulse" style={{ color: "var(--th-primary)" }}>
            ● CONTINUOUS LOOP
          </span>
        )}
        {wakeWordEnabled && (
          <span className="text-emerald-400 animate-pulse">
            ● LISTENING FOR &quot;HEY MEERO&quot;
          </span>
        )}
      </div>
    </div>
  );
}

export default App;
