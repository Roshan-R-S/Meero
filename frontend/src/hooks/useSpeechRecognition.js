import { useCallback, useEffect, useRef, useState } from "react";
import { playListeningStart, playListeningStop } from "../utils/sound";
import { logger } from "../utils/logger";
import { getBrowserSpeechRecognition } from "../utils/speechSupport";

const WAKE_VARIANTS = [
  "hey meero", "hey miro", "a meero", "hey mirror", "hey nero",
  "hey mero", "hey mira", "hey mural", "meero", "miro",
];

const clean = (text) =>
  text.toLowerCase().replace(/[.,!?;:'"]/g, "").replace(/\s+/g, " ").trim();

const useSpeechRecognition = (onResult, currentState, setState, onInterrupt = null) => {
  const recRef = useRef(null);
  const stateRef = useRef(currentState);
  const [isConversing, setIsConversing] = useState(false);
  const isConversingRef = useRef(false);
  const [recognitionError, setRecognitionError] = useState("");

  // WAKE WORD & CONTINUED CONVERSATION
  const [wakeWordEnabled, setWakeWordEnabled] = useState(false);
  const wakeRef = useRef(false);       // Enabled toggle
  const wakeActiveRef = useRef(false); // true = waiting for command (active listening)
  const manualRef = useRef(false);     // true = push-to-talk
  const timerRef = useRef(null);

  useEffect(() => { stateRef.current = currentState; }, [currentState]);
  useEffect(() => { wakeRef.current = wakeWordEnabled; }, [wakeWordEnabled]);
  const cbRef = useRef(onResult);
  useEffect(() => { cbRef.current = onResult; }, [onResult]);
  const interruptRef = useRef(onInterrupt);
  useEffect(() => { interruptRef.current = onInterrupt; }, [onInterrupt]);

  // ── Restart Helper ─────────────────────────────────────────────
  const restartWake = useCallback((ms = 150) => {
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      // Don't restart if disabled OR manual mode OR speaking
      if (!wakeRef.current || manualRef.current) return;
      if (stateRef.current === "processing" || stateRef.current === "speaking") return;

      logger.log(`[Wake] Restarting... active=${wakeActiveRef.current}`);
      try { recRef.current?.start(); } catch { /* running */ }
    }, ms);
  }, []);

  // ── Start Active Listening (Continued Conversation) ────────────
  const startActiveListening = useCallback(() => {
    if (!recRef.current) return;
    logger.log("[Wake] Starting ACTIVE listening (Continued Conversation)");
    wakeActiveRef.current = true;
    try { recRef.current.start(); } catch { /* running */ }
  }, []);

  // ── Init Recognition ───────────────────────────────────────────
  useEffect(() => {
    const SpeechAPI = getBrowserSpeechRecognition();
    if (!SpeechAPI) return;
    if (!recRef.current) recRef.current = new SpeechAPI();
    const rec = recRef.current;
    rec.continuous = false; // Must be false for robust resets
    rec.interimResults = false;
    rec.lang = "en-US";

    rec.onstart = () => {
      const mode = manualRef.current ? "MANUAL" : wakeActiveRef.current ? "ACTIVE" : "PASSIVE";
      logger.log(`[Speech] Started (${mode})`);
      setRecognitionError("");
      
      // Visual feedback only for Manual or Active mode
      if (manualRef.current || wakeActiveRef.current) {
        setState("listening");
        playListeningStart();
      }
    };

    rec.onresult = (e) => {
      const text = clean(e.results[0][0].transcript);
      logger.log("[Heard]", text);

      // MANUAL
      if (manualRef.current) {
        manualRef.current = false;
        playListeningStop();
        cbRef.current(text);
        return;
      }

      // WAKE PASSIVE (scanning for wake word)
      if (wakeRef.current && !wakeActiveRef.current) {
        if (WAKE_VARIANTS.some((w) => text.includes(w))) {
          logger.log("[Wake] Detected!");
          // Check for inline command: "Hey Meero open YouTube"
          let cmd = text;
          for (const v of WAKE_VARIANTS) cmd = cmd.replace(v, "").trim();
          cmd = cmd.replace(/^(hey|hi|hello)\s*/i, "").trim();

          if (cmd.length > 2) {
            playListeningStart();
            playListeningStop();
            if (interruptRef.current) interruptRef.current();
            setState("processing");
            cbRef.current(cmd);
          } else {
            // "Hey Meero" -> Switch to Active
            wakeActiveRef.current = true;
            if (interruptRef.current) interruptRef.current();
            setState("listening");
            playListeningStart();
          }
        }
        return; // wait for onend to loop
      }

      // WAKE ACTIVE (Continued Conversation / Command)
      if (wakeRef.current && wakeActiveRef.current) {
        wakeActiveRef.current = false; // Reset active flag on success
        playListeningStop();
        setState("processing");
        cbRef.current(text);
        return;
      }

      // Fallback
      playListeningStop();
      cbRef.current(text);
    };

    rec.onerror = (e) => {
      if (e.error === "not-allowed") {
        manualRef.current = false;
        setRecognitionError("Microphone permission denied.");
        setState("idle");
      } else {
        setRecognitionError("Speech recognition stopped.");
      }
    };

    rec.onend = () => {
      // Manual -> handled by toggleListen
      if (manualRef.current) return;

      // Wake Mode -> handled by restart logic
      if (wakeRef.current) {
        if (stateRef.current === "processing" || stateRef.current === "speaking") return;

        // If we were in ACTIVE mode and it ended without result (silence/timeout),
        // revert to PASSIVE mode for the next loop.
        if (wakeActiveRef.current) {
          logger.log("[Wake] Active window timed out -> Reverting to Passive");
          wakeActiveRef.current = false;
        }

        restartWake(150);
        return;
      }

      setState((p) => (p === "listening" ? "idle" : p));
    };

    return () => clearTimeout(timerRef.current);
  }, [setState, restartWake]);

  // ── Toggles ────────────────────────────────────────────────────
  useEffect(() => {
    if (wakeWordEnabled) {
      manualRef.current = false;
      wakeActiveRef.current = false;
      restartWake(200);
    } else {
      clearTimeout(timerRef.current);
      wakeActiveRef.current = false;
      try { recRef.current?.abort(); } catch { /* */ }
      setState("idle");
    }
  }, [wakeWordEnabled, restartWake, setState]);

  useEffect(() => {
    if (currentState === "idle" && wakeRef.current && !manualRef.current) {
      restartWake(300);
    }
  }, [currentState, restartWake]);

  // ── Mic Button ─────────────────────────────────────────────────
  const toggleListen = useCallback(() => {
    const rec = recRef.current;
    if (!rec) return;
    clearTimeout(timerRef.current);

    if (stateRef.current === "listening") {
      manualRef.current = false;
      wakeActiveRef.current = false;
      try { rec.abort(); } catch { /* */ }
      playListeningStop();
      setIsConversing(false);
      isConversingRef.current = false;
      setState("idle");
    } else {
      manualRef.current = true;
      wakeActiveRef.current = false;
      setIsConversing(true);
      isConversingRef.current = true;
      if (interruptRef.current) interruptRef.current();
      try { rec.abort(); } catch { /* */ }
      
      timerRef.current = setTimeout(() => {
        if (!manualRef.current) return;
        try { rec.start(); } catch {
          setTimeout(() => { try { rec.start(); } catch { manualRef.current = false; setState("idle"); } }, 200);
        }
      }, 150);
    }
  }, [setState]);

  return {
    isConversing, isConversingRef, toggleListen,
    recognitionRef: recRef, wakeWordEnabled, setWakeWordEnabled,
    startActiveListening, // Expose for Continued Conversation
    recognitionError,
  };
};

export default useSpeechRecognition;
