import { useCallback, useEffect, useRef } from "react";
import { API_URL, AUTH_VALUE, streamVoiceSynthesis } from "../api";
import { logger } from "../utils/logger";
import { AudioChunkQueue } from "./useVoicePipeline";

/**
 * Hook for TTS output.
 * - When localVoiceEnabled=true: streams audio from /voice/synthesize/stream (XTTS cloned voice).
 * - Fallback: /voice/synthesize blob or browser Web Speech API.
 */
const useSpeechSynthesis = (setState, onComplete, voiceConfig = {}, localVoiceEnabled = false) => {
  const synth = useRef(null);
  const audioRef = useRef(null);
  const chunkQueueRef = useRef(null);

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

      const voices = synth.current.getVoices?.() || [];
      const preferredVoice =
        voices.find((v) => v.lang?.startsWith("en") && (v.localService || v.default)) ||
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
      let receivedChunk = false;

      // Stop previous chunk queue or audio
      if (chunkQueueRef.current) {
        chunkQueueRef.current.stop();
        chunkQueueRef.current = null;
      }
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }

      try {
        const queue = new AudioChunkQueue(
          () => setState("speaking"),
          () => {
            logger.log("[TTS] XTTS playback finished -> triggering onComplete");
            setState("idle");
            if (onComplete) onComplete();
          },
        );
        chunkQueueRef.current = queue;

        await streamVoiceSynthesis(text, (event) => {
          if (event.type === "audio_chunk" && event.audio_base64) {
            receivedChunk = true;
            queue.enqueue(event.audio_base64, event.mime_type || "audio/wav");
          } else if (event.type === "done") {
            queue.markDone();
          } else if (event.type === "error") {
            throw new Error(event.message || "TTS stream error");
          }
        });

        if (!receivedChunk) {
          throw new Error("No audio chunks received from stream");
        }
      } catch (err) {
        logger.error("[TTS] XTTS streaming synthesis failed, falling back to full synthesis/browser TTS:", err);
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

          audio.onerror = (audioErr) => {
            URL.revokeObjectURL(url);
            audioRef.current = null;
            logger.error("[TTS] XTTS audio playback error:", audioErr);
            _playBrowserTTS(text);
          };

          await audio.play();
        } catch (fallbackErr) {
          logger.error("[TTS] Full synthesis also failed, falling back to browser TTS:", fallbackErr);
          _playBrowserTTS(text);
        }
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
    // Cancel streamed audio queue
    if (chunkQueueRef.current) {
      chunkQueueRef.current.stop();
      chunkQueueRef.current = null;
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
