import { useCallback, useRef, useState } from "react";
import { localAudioCaptureSupported } from "../utils/speechSupport";

const SILENCE_THRESHOLD = 0.012;
const SILENCE_TIMEOUT_MS = 1200;

const writeString = (view, offset, value) => {
  for (let index = 0; index < value.length; index += 1) {
    view.setUint8(offset + index, value.charCodeAt(index));
  }
};

const encodeWav = (samples, sampleRate) => {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, "WAVE");
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(view, 36, "data");
  view.setUint32(40, samples.length * 2, true);
  samples.forEach((sample, index) => {
    const clamped = Math.max(-1, Math.min(1, sample));
    view.setInt16(44 + index * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
  });
  return new Blob([view], { type: "audio/wav" });
};

const resample = (samples, inputRate, outputRate = 16000) => {
  if (inputRate === outputRate) return samples;
  const outputLength = Math.max(1, Math.round(samples.length * outputRate / inputRate));
  const output = new Float32Array(outputLength);
  for (let index = 0; index < outputLength; index += 1) {
    const sourceIndex = index * inputRate / outputRate;
    const lower = Math.floor(sourceIndex);
    const upper = Math.min(lower + 1, samples.length - 1);
    const mix = sourceIndex - lower;
    output[index] = samples[lower] * (1 - mix) + samples[upper] * mix;
  }
  return output;
};

export default function useAudioRecorder() {
  const [recording, setRecording] = useState(false);
  const contextRef = useRef(null);
  const processorRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const onStopRef = useRef(null);
  const hasVoiceRef = useRef(false);
  const lastVoiceAtRef = useRef(0);
  const stoppingRef = useRef(false);

  const cleanup = useCallback(async () => {
    processorRef.current?.disconnect();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    await contextRef.current?.close?.();
    processorRef.current = null;
    streamRef.current = null;
    contextRef.current = null;
    onStopRef.current = null;
    hasVoiceRef.current = false;
    lastVoiceAtRef.current = 0;
    stoppingRef.current = false;
    setRecording(false);
  }, []);

  const finalizeRecording = useCallback(async () => {
    const sampleRate = contextRef.current?.sampleRate || 16000;
    const length = chunksRef.current.reduce((total, chunk) => total + chunk.length, 0);
    const samples = new Float32Array(length);
    let offset = 0;
    chunksRef.current.forEach((chunk) => {
      samples.set(chunk, offset);
      offset += chunk.length;
    });
    await cleanup();
    if (!samples.length) throw new Error("No audio was captured.");
    return encodeWav(resample(samples, sampleRate), 16000);
  }, [cleanup]);

  const stopRecording = useCallback(async () => {
    if (!recording) throw new Error("Recorder is not active.");
    return finalizeRecording();
  }, [finalizeRecording, recording]);

  const startRecording = useCallback(async ({ onStop } = {}) => {
    if (!localAudioCaptureSupported()) throw new Error("Local audio capture is unavailable.");
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1 } });
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    const context = new AudioContext({ sampleRate: 16000 });
    const source = context.createMediaStreamSource(stream);
    const processor = context.createScriptProcessor(4096, 1, 1);
    chunksRef.current = [];
    onStopRef.current = onStop || null;
    hasVoiceRef.current = false;
    lastVoiceAtRef.current = 0;
    stoppingRef.current = false;
    processor.onaudioprocess = (event) => {
      const input = event.inputBuffer.getChannelData(0);
      chunksRef.current.push(new Float32Array(input));
      let sumSquares = 0;
      for (let index = 0; index < input.length; index += 1) {
        sumSquares += input[index] * input[index];
      }
      const rms = Math.sqrt(sumSquares / Math.max(1, input.length));
      const now = Date.now();

      if (rms >= SILENCE_THRESHOLD) {
        hasVoiceRef.current = true;
        lastVoiceAtRef.current = now;
        return;
      }

      if (!hasVoiceRef.current || stoppingRef.current) return;
      if (now - lastVoiceAtRef.current < SILENCE_TIMEOUT_MS) return;

      stoppingRef.current = true;
      const autoStop = onStopRef.current;
      void finalizeRecording()
        .then((audio) => autoStop?.(audio))
        .catch(() => {
          /* Auto-stop failures are handled by the manual stop path. */
        });
    };
    source.connect(processor);
    processor.connect(context.destination);
    contextRef.current = context;
    processorRef.current = processor;
    streamRef.current = stream;
    setRecording(true);
  }, [finalizeRecording]);

  const cancelRecording = useCallback(async () => {
    chunksRef.current = [];
    await cleanup();
  }, [cleanup]);

  return {
    supported: localAudioCaptureSupported(),
    recording,
    startRecording,
    stopRecording,
    cancelRecording,
  };
}
