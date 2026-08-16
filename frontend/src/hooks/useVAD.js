/**
 * useVAD — Silero VAD (Voice Activity Detection) hook.
 *
 * Loads the Silero VAD ONNX model from /silero_vad.onnx (served from
 * frontend/public/) via onnxruntime-web and exposes a per-frame speech
 * probability detector.
 *
 * Graceful degradation: if the ONNX model fails to load (missing file,
 * browser does not support WebAssembly, etc.) vadReady stays false and
 * callers fall back to the RMS-threshold path in useAudioRecorder.
 *
 * Usage:
 *   const { vadReady, startVAD, stopVAD } = useVAD();
 *
 *   startVAD((samples, probability) => {
 *     // samples: Float32Array of the current audio frame (512 samples @ 16 kHz)
 *     // probability: 0–1 speech likelihood for this frame
 *   });
 *
 *   stopVAD(); // resets the LSTM hidden state for the next recording
 */

import { useCallback, useRef, useState } from "react";
import { logger } from "../utils/logger";

/** Silero VAD expects exactly 512 samples per frame at 16 kHz (32 ms). */
export const VAD_FRAME_SAMPLES = 512;
export const VAD_SAMPLE_RATE = 16000;

/** Speech probability thresholds */
export const VAD_SPEECH_THRESHOLD = 0.5;
export const VAD_SILENCE_THRESHOLD = 0.35;

export default function useVAD() {
  const [vadReady, setVadReady] = useState(false);
  const sessionRef = useRef(null);
  const loadingRef = useRef(false);
  const callbackRef = useRef(null);

  // Silero VAD stateful LSTM hidden state (h, c) — must persist across frames
  // within a single recording session, reset between sessions.
  const stateRef = useRef(null);

  const _initState = useCallback(() => {
    // h and c: [2, 1, 64] float32 tensors, zeroed
    const zeros = new Float32Array(2 * 1 * 64);
    stateRef.current = { h: zeros.slice(), c: zeros.slice() };
  }, []);

  /**
   * Lazily load the ONNX model and InferenceSession. Called once on first
   * startVAD() call and cached for the lifetime of the component.
   */
  const _loadModel = useCallback(async () => {
    if (sessionRef.current || loadingRef.current) return;
    loadingRef.current = true;
    try {
      // Dynamic import so onnxruntime-web is code-split and only loaded when needed
      const ort = await import("onnxruntime-web");

      // Point the WASM backend at the default /ort-wasm-*.wasm paths served by Vite
      ort.env.wasm.wasmPaths = "/";

      const session = await ort.InferenceSession.create("/silero_vad.onnx", {
        executionProviders: ["wasm"],
        graphOptimizationLevel: "all",
      });

      sessionRef.current = session;
      setVadReady(true);
      logger.log("[VAD] Silero VAD model loaded successfully");
    } catch (err) {
      logger.log("[VAD] Failed to load ONNX model, falling back to RMS:", err?.message);
      // vadReady stays false — recorder falls back to RMS threshold
    } finally {
      loadingRef.current = false;
    }
  }, []);

  /**
   * Run a single VAD inference frame.
   * Returns the speech probability (0–1) for the given 512-sample frame.
   * Returns null if the session is not ready.
   */
  const _infer = useCallback(async (samples) => {
    const session = sessionRef.current;
    if (!session || !stateRef.current) return null;

    try {
      const ort = await import("onnxruntime-web");
      const { Tensor } = ort;

      // Input: [1, 512] float32
      const inputTensor = new Tensor("float32", samples, [1, VAD_FRAME_SAMPLES]);

      // Sample rate tensor: int64 scalar
      const srTensor = new Tensor("int64", BigInt64Array.from([BigInt(VAD_SAMPLE_RATE)]), []);

      // Hidden state tensors: [2, 1, 64]
      const hTensor = new Tensor("float32", stateRef.current.h, [2, 1, 64]);
      const cTensor = new Tensor("float32", stateRef.current.c, [2, 1, 64]);

      const feeds = {
        input: inputTensor,
        sr: srTensor,
        h: hTensor,
        c: cTensor,
      };

      const results = await session.run(feeds);

      // Update hidden state for next frame
      stateRef.current.h = results.hn.data.slice();
      stateRef.current.c = results.cn.data.slice();

      // Output probability
      return results.output.data[0];
    } catch (err) {
      logger.log("[VAD] Inference error:", err?.message);
      return null;
    }
  }, []);

  /**
   * Start VAD session. Loads the model lazily on first call.
   * @param {function(Float32Array, number): void} onFrame - called per 512-sample frame
   */
  const startVAD = useCallback(async (onFrame) => {
    callbackRef.current = onFrame;
    _initState();
    await _loadModel();
  }, [_loadModel, _initState]);

  /**
   * Stop VAD session and reset LSTM state for the next recording.
   */
  const stopVAD = useCallback(() => {
    callbackRef.current = null;
    stateRef.current = null;
  }, []);

  /**
   * Process a chunk of audio samples from the ScriptProcessorNode.
   * Splits the buffer into 512-sample VAD frames, runs inference on each,
   * and calls the registered onFrame callback.
   *
   * Returns the average speech probability across all frames in this chunk,
   * or null if VAD is not ready.
   */
  const processAudioChunk = useCallback(async (inputSamples) => {
    if (!sessionRef.current || !stateRef.current || !callbackRef.current) return null;

    let totalProb = 0;
    let frameCount = 0;

    for (let offset = 0; offset + VAD_FRAME_SAMPLES <= inputSamples.length; offset += VAD_FRAME_SAMPLES) {
      const frame = inputSamples.subarray(offset, offset + VAD_FRAME_SAMPLES);
      const prob = await _infer(frame);
      if (prob !== null) {
        callbackRef.current(frame, prob);
        totalProb += prob;
        frameCount++;
      }
    }

    return frameCount > 0 ? totalProb / frameCount : null;
  }, [_infer]);

  return { vadReady, startVAD, stopVAD, processAudioChunk };
}
