import { useCallback, useEffect, useRef, useState } from "react";
import { sendVoiceCommand, streamVoiceCommand } from "../api";
import { logger } from "../utils/logger";
import useAudioRecorder from "./useAudioRecorder";
import useVAD from "./useVAD";

export class AudioChunkQueue {
  constructor(onPlaybackStart, onPlaybackEnd) {
    this.queue = [];
    this.isPlaying = false;
    this.onPlaybackStart = onPlaybackStart;
    this.onPlaybackEnd = onPlaybackEnd;
    this.isDoneEmitted = false;
  }

  enqueue(audioBase64, mimeType = "audio/wav") {
    if (!audioBase64) return;
    this.queue.push({ audioBase64, mimeType });
    if (!this.isPlaying) {
      this._playNext();
    }
  }

  markDone() {
    this.isDoneEmitted = true;
    if (!this.isPlaying && this.queue.length === 0) {
      this.onPlaybackEnd?.();
    }
  }

  _playNext() {
    if (this.queue.length === 0) {
      this.isPlaying = false;
      if (this.isDoneEmitted) {
        this.onPlaybackEnd?.();
      }
      return;
    }

    if (!this.isPlaying) {
      this.isPlaying = true;
      this.onPlaybackStart?.();
    }

    const item = this.queue.shift();
    try {
      let url;
      let isObjectUrl = false;
      if (typeof URL !== "undefined" && typeof URL.createObjectURL === "function") {
        try {
          const byteChars = atob(item.audioBase64);
          const byteNumbers = new Uint8Array(byteChars.length);
          for (let i = 0; i < byteChars.length; i++) {
            byteNumbers[i] = byteChars.charCodeAt(i);
          }
          const blob = new Blob([byteNumbers], { type: item.mimeType || "audio/wav" });
          url = URL.createObjectURL(blob);
          isObjectUrl = true;
        } catch {
          url = `data:${item.mimeType || "audio/wav"};base64,${item.audioBase64}`;
        }
      } else {
        url = `data:${item.mimeType || "audio/wav"};base64,${item.audioBase64}`;
      }
      const audio = new Audio(url);

      const cleanupAndNext = () => {
        if (isObjectUrl && typeof URL !== "undefined" && typeof URL.revokeObjectURL === "function") {
          URL.revokeObjectURL(url);
        }
        this._playNext();
      };

      audio.onended = cleanupAndNext;
      audio.onerror = (err) => {
        logger.error("[AudioChunkQueue] Audio element error:", err);
        cleanupAndNext();
      };
      audio.play().catch((err) => {
        logger.error("[AudioChunkQueue] Audio play rejection:", err);
        cleanupAndNext();
      });
    } catch (err) {
      logger.error("[AudioChunkQueue] Playback setup error:", err);
      this._playNext();
    }
  }

  stop() {
    this.queue = [];
    this.isPlaying = false;
    this.isDoneEmitted = false;
    this.onPlaybackEnd?.();
  }
}

const playBase64Wav = (audioBase64, mimeType = "audio/wav") =>
  new Promise((resolve) => {
    if (!audioBase64) {
      resolve();
      return;
    }
    const audio = new Audio(`data:${mimeType};base64,${audioBase64}`);
    audio.onended = resolve;
    audio.onerror = resolve;
    audio.play().catch(resolve);
  });

export default function useVoicePipeline({ onResult, pendingCommand, setState }) {
  const recorder = useAudioRecorder();
  const { vadReady, startVAD, stopVAD, processAudioChunk } = useVAD();
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState("");

  // Live mic energy for orb visualizer (0–1, smoothed)
  const micEnergyLevel = recorder.recording ? recorder.micEnergyLevel : 0;

  const resultRef = useRef(onResult);
  useEffect(() => {
    resultRef.current = onResult;
  }, [onResult]);

  const submitAudio = useCallback(async (audio) => {
    stopVAD();

    if (typeof streamVoiceCommand === "function") {
      try {
        let finalOutcome = null;
        const queue = new AudioChunkQueue(
          () => setState?.("speaking"),
          () => setState?.("idle")
        );

        let streamHandled = false;
        let currentTranscript = "";
        await streamVoiceCommand(
          audio,
          { pendingCommand, audioMode: "chunked", fastAck: false },
          async (event) => {
            streamHandled = true;
            if (event.type === "transcript") {
              currentTranscript = event.text || "";
            } else if (event.type === "text_final") {
              finalOutcome = {
                transcript: event.transcript || currentTranscript || "",
                response: event.response,
                action_status: event.action_status,
                sentiment: event.sentiment,
                pending_command: event.pending_command,
                metadata: event.metadata || {},
                streaming: true,
              };
              await resultRef.current?.(finalOutcome);
            } else if (event.type === "audio_chunk") {
              queue.enqueue(event.audio_base64, event.mime_type);
            } else if (event.type === "done") {
              queue.markDone();
            } else if (event.type === "error") {
              logger.error("[useVoicePipeline] Stream event error:", event.message);
              setError(event.message || "Voice stream error");
            }
          }
        );

        if (streamHandled) {
          return;
        }
      } catch (streamErr) {
        logger.error("[useVoicePipeline] Stream connection error, falling back:", streamErr);
      }
    }

    const result = await sendVoiceCommand(audio, { pendingCommand });
    await resultRef.current?.(result);
    if (result.audio_base64) {
      setState?.("speaking");
      void playBase64Wav(result.audio_base64, result.audio_mime_type).finally(() => {
        setState?.("idle");
      });
    }
  }, [pendingCommand, setState, stopVAD]);

  const toggleRecording = useCallback(async () => {
    setError("");
    try {
      if (!recorder.recording) {
        // Start VAD session before starting recorder so model is ready
        await startVAD();

        await recorder.startRecording({
          onStop: async (audio) => {
            setProcessing(true);
            try {
              await submitAudio(audio);
            } finally {
              setProcessing(false);
            }
          },
          processAudioChunk: vadReady ? processAudioChunk : undefined,
        });
        return;
      }

      setProcessing(true);
      const audio = await recorder.stopRecording();
      await submitAudio(audio);
    } catch (voiceError) {
      setError(voiceError?.message || "Local voice processing failed.");
    } finally {
      setProcessing(false);
    }
  }, [recorder, submitAudio, startVAD, vadReady, processAudioChunk]);

  return {
    ...recorder,
    processing,
    error,
    toggleRecording,
    micEnergyLevel,
    vadReady,
  };
}
