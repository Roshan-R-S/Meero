import { Mic, Radio, StopCircle } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { sendCommand } from "./api";
import Background from "./components/Background";
import HologramOverlay from "./components/HologramOverlay";
import ThreeOrb from "./components/ThreeOrb";
import useSpeechRecognition from "./hooks/useSpeechRecognition";
import useSpeechSynthesis from "./hooks/useSpeechSynthesis";
import "./index.css";
import { playProcessing, playStartup } from "./utils/sound";

function App() {
  const [state, setState] = useState("idle"); // idle, listening, processing, speaking
  const [sentiment, setSentiment] = useState("neutral"); // neutral, positive, negative

  // -- BOOT SEQUENCE STATE --
  const [booting, setBooting] = useState(true);

  // Startup Sound
  useEffect(() => {
    const hasInteracted = localStorage.getItem("hasInteracted");
    const handleFirstClick = () => {
      playStartup();
      localStorage.setItem("hasInteracted", "true");
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
  } = useSpeechRecognition(
    (text) => handleCommandRef.current(text),
    state,
    setState,
  );

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
  );

  const handleCommand = useCallback(async (text) => {
    if (!text.trim()) return;
    setState("processing");
    playProcessing();

    const data = await sendCommand(text);
    if (data.sentiment) setSentiment(data.sentiment);
    speakRef.current(data.response);
  }, []);

  // Keep refs in sync (must be in effect, not during render)
  useEffect(() => {
    speakRef.current = speak;
    handleCommandRef.current = handleCommand;
  }, [speak, handleCommand]);

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
      <Background />
      <HologramOverlay />

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
            onClick={toggleListen}
            aria-label={
              state === "listening" ? "Stop listening" : "Start listening"
            }
            className={`p-6 rounded-full transition-all duration-300 transform hover:scale-105 active:scale-95 ${
              state === "listening"
                ? "bg-red-500/90 shadow-[0_0_40px_rgba(239,68,68,0.6)] animate-pulse"
                : "bg-cyan-600/90 hover:bg-cyan-500 shadow-[0_0_30px_rgba(8,145,178,0.4)]"
            }`}
          >
            {state === "listening" ? (
              <StopCircle size={32} />
            ) : (
              <Mic size={32} />
            )}
          </button>
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
