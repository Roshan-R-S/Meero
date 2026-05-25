import { useCallback, useRef } from "react";

/**
 * Hook for TTS with Jarvis-like voice config.
 * @param {Function} setState - App state setter
 * @param {Function} onComplete - Callback when speaking finishes (for restarting recognition)
 */
const useSpeechSynthesis = (setState, onComplete) => {
  const synth = useRef(window.speechSynthesis);

  const speak = useCallback(
    (text) => {
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

      utterance.pitch = 0.9;
      utterance.rate = 1.0;

      utterance.onend = () => {
        console.log("[TTS] Finished speaking -> triggering onComplete");
        setState("idle");
        if (onComplete) onComplete();
      };

      synth.current.speak(utterance);
    },
    [setState, onComplete],
  );

  return { speak };
};

export default useSpeechSynthesis;
