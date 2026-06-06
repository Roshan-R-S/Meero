import { useCallback, useEffect, useRef } from "react";
import { logger } from "../utils/logger";

/**
 * Hook for TTS with Jarvis-like voice config.
 * @param {Function} setState - App state setter
 * @param {Function} onComplete - Callback when speaking finishes (for restarting recognition)
 */
const useSpeechSynthesis = (setState, onComplete, voiceConfig = {}) => {
  const synth = useRef(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      synth.current = window.speechSynthesis;
    }
  }, []);

  const speak = useCallback(
    (text) => {
      if (!synth.current && typeof window !== "undefined") {
        synth.current = window.speechSynthesis;
      }
      if (!synth.current) return;

      if (synth.current.speaking) synth.current.cancel();

      setState("speaking");
      const utterance = new SpeechSynthesisUtterance(text);

      const voices = synth.current.getVoices();
      const preferredVoice =
        voices.find(
          (v) =>
            v.name.includes("Google UK English Male") ||
            v.name.includes("Microsoft George"),
        ) ||
        voices.find((v) => v.name.includes("Google US English")) ||
        voices[0];
      if (preferredVoice) utterance.voice = preferredVoice;

      utterance.pitch = voiceConfig.pitch ?? 0.9;
      utterance.rate = voiceConfig.rate ?? 1.0;

      utterance.onend = () => {
        logger.log("[TTS] Finished speaking -> triggering onComplete");
        setState("idle");
        if (onComplete) onComplete();
      };

      synth.current.speak(utterance);
    },
    [setState, onComplete, voiceConfig.pitch, voiceConfig.rate],
  );

  const cancel = useCallback(() => {
    if (synth.current && synth.current.speaking) {
      synth.current.cancel();
      setState("idle");
    }
  }, [setState]);

  return { speak, cancel };
};

export default useSpeechSynthesis;
