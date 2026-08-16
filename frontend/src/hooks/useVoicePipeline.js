import { useCallback, useEffect, useRef, useState } from "react";
import { sendVoiceCommand } from "../api";
import useAudioRecorder from "./useAudioRecorder";
import useVAD from "./useVAD";

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
          // Wire VAD inference into the recorder when model is ready
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
