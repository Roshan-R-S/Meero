import { useCallback, useEffect, useRef, useState } from "react";
import { sendVoiceCommand } from "../api";
import useAudioRecorder from "./useAudioRecorder";

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
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState("");
  const resultRef = useRef(onResult);
  useEffect(() => {
    resultRef.current = onResult;
  }, [onResult]);

  const submitAudio = useCallback(async (audio) => {
    const result = await sendVoiceCommand(audio, { pendingCommand });
    await resultRef.current?.(result);
    if (result.audio_base64) {
      setState?.("speaking");
      void playBase64Wav(result.audio_base64, result.audio_mime_type).finally(() => {
        setState?.("idle");
      });
    }
  }, [pendingCommand, setState]);

  const toggleRecording = useCallback(async () => {
    setError("");
    try {
      if (!recorder.recording) {
        await recorder.startRecording({ onStop: async (audio) => {
          setProcessing(true);
          try {
            await submitAudio(audio);
          } finally {
            setProcessing(false);
          }
        } });
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
  }, [pendingCommand, recorder, submitAudio]);

  return { ...recorder, processing, error, toggleRecording };
}
