import { useCallback, useEffect, useRef } from "react";
import { API_URL, AUTH_VALUE } from "../api";
import { logger } from "../utils/logger";

/**
 * Hook for TTS output.
 * - When localVoiceEnabled=true: sends text to /voice/synthesize (XTTS cloned voice).
 * - Fallback: browser Web Speech API.
 */
const useSpeechSynthesis = (setState, onComplete, voiceConfig = {}, localVoiceEnabled = false) => {
  const synth = useRef(null);
  const audioRef = useRef(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      synth.current = window.speechSynthesis;
    }
  }, []);

  const _playBrowserTTS = useCallback(
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
        voices.find((v) => v.lang?.startsWith("en") && v.name.toLowerCase().includes("female")) ||
        voices.find((v) => v.lang?.startsWith("en")) ||
        voices[0];
      if (preferredVoice) utterance.voice = preferredVoice;

      utterance.pitch = voiceConfig.pitch ?? 1.0;
      utterance.rate = voiceConfig.rate ?? 1.0;

      utterance.onend = () => {
        logger.log("[TTS] Browser speech finished -> triggering onComplete");
        setState("idle");
        if (onComplete) onComplete();
      };

      synth.current.speak(utterance);
    },
    [setState, onComplete, voiceConfig.pitch, voiceConfig.rate],
  );

  const _playLocalXTTS = useCallback(
    async (text) => {
      setState("speaking");
      try {
        const headers = { "Content-Type": "application/json" };
        if (AUTH_VALUE) headers["x-meero-api-key"] = AUTH_VALUE;

        const res = await fetch(`${API_URL}/voice/synthesize`, {
          method: "POST",
          headers,
          body: JSON.stringify({ text }),
        });

        if (!res.ok) throw new Error(`TTS HTTP ${res.status}`);

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);

        // Stop any currently playing audio
        if (audioRef.current) {
          audioRef.current.pause();
          audioRef.current = null;
        }

        const audio = new Audio(url);
        audioRef.current = audio;

        audio.onended = () => {
          URL.revokeObjectURL(url);
          audioRef.current = null;
          logger.log("[TTS] XTTS playback finished -> triggering onComplete");
          setState("idle");
          if (onComplete) onComplete();
        };

        audio.onerror = (err) => {
          URL.revokeObjectURL(url);
          audioRef.current = null;
          logger.error("[TTS] XTTS audio playback error:", err);
          setState("idle");
          if (onComplete) onComplete();
        };

        await audio.play();
      } catch (err) {
        logger.error("[TTS] XTTS synthesis failed, falling back to browser TTS:", err);
        _playBrowserTTS(text);
      }
    },
    [setState, onComplete, _playBrowserTTS],
  );

  const speak = useCallback(
    (text) => {
      if (localVoiceEnabled) {
        _playLocalXTTS(text);
      } else {
        _playBrowserTTS(text);
      }
    },
    [localVoiceEnabled, _playLocalXTTS, _playBrowserTTS],
  );

  const cancel = useCallback(() => {
    // Cancel browser TTS
    if (synth.current && synth.current.speaking) {
      synth.current.cancel();
    }
    // Cancel XTTS audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setState("idle");
  }, [setState]);

  return { speak, cancel };
};

export default useSpeechSynthesis;
