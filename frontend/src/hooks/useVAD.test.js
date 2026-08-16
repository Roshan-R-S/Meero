/**
 * useVAD.test.js — unit tests for the Silero VAD hook.
 *
 * Tests cover:
 *  1. Happy path: model loads, processAudioChunk returns probability
 *  2. Graceful failure: onnxruntime-web unavailable → vadReady stays false
 *  3. stopVAD resets state so a second session starts clean
 */
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

// ── Mocks ────────────────────────────────────────────────────────────────────

const mocks = vi.hoisted(() => ({
  InferenceSession: {
    create: vi.fn(),
  },
  Tensor: vi.fn(),
  env: { wasm: { wasmPaths: "" } },
}));

// Mock onnxruntime-web module
vi.mock("onnxruntime-web", () => ({
  InferenceSession: mocks.InferenceSession,
  Tensor: mocks.Tensor,
  env: mocks.env,
}));

import useVAD, { VAD_FRAME_SAMPLES } from "./useVAD";

// ── Helpers ──────────────────────────────────────────────────────────────────

const makeSession = (outputProb = 0.85) => ({
  run: vi.fn().mockResolvedValue({
    output: { data: [outputProb] },
    hn: { data: new Float32Array(2 * 1 * 64) },
    cn: { data: new Float32Array(2 * 1 * 64) },
  }),
});

const makeSamples = (count = VAD_FRAME_SAMPLES) => new Float32Array(count).fill(0.1);

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("useVAD", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.Tensor.mockImplementation((type, data, shape) => ({ type, data, shape }));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("vadReady starts false", () => {
    const { result } = renderHook(() => useVAD());
    expect(result.current.vadReady).toBe(false);
  });

  test("vadReady becomes true after model loads successfully", async () => {
    const session = makeSession();
    mocks.InferenceSession.create.mockResolvedValue(session);

    const { result } = renderHook(() => useVAD());

    await act(async () => {
      await result.current.startVAD(vi.fn());
    });

    expect(result.current.vadReady).toBe(true);
    expect(mocks.InferenceSession.create).toHaveBeenCalledWith(
      "/silero_vad.onnx",
      expect.objectContaining({ executionProviders: ["wasm"] }),
    );
  });

  test("vadReady stays false when onnxruntime-web throws", async () => {
    mocks.InferenceSession.create.mockRejectedValue(new Error("WASM not supported"));

    const { result } = renderHook(() => useVAD());

    await act(async () => {
      await result.current.startVAD(vi.fn());
    });

    expect(result.current.vadReady).toBe(false);
  });

  test("processAudioChunk invokes the onFrame callback with probability", async () => {
    const session = makeSession(0.92);
    mocks.InferenceSession.create.mockResolvedValue(session);

    const { result } = renderHook(() => useVAD());
    const onFrame = vi.fn();

    await act(async () => {
      await result.current.startVAD(onFrame);
    });

    let avgProb;
    await act(async () => {
      avgProb = await result.current.processAudioChunk(makeSamples(VAD_FRAME_SAMPLES));
    });

    expect(onFrame).toHaveBeenCalledOnce();
    expect(onFrame).toHaveBeenCalledWith(expect.any(Float32Array), expect.closeTo(0.92, 2));
    expect(avgProb).toBeCloseTo(0.92, 2);
  });

  test("processAudioChunk handles multiple frames in one chunk", async () => {
    const session = makeSession(0.7);
    mocks.InferenceSession.create.mockResolvedValue(session);

    const { result } = renderHook(() => useVAD());
    const onFrame = vi.fn();

    await act(async () => {
      await result.current.startVAD(onFrame);
    });

    // 3 full VAD frames in one chunk
    const samples = makeSamples(VAD_FRAME_SAMPLES * 3);
    await act(async () => {
      await result.current.processAudioChunk(samples);
    });

    expect(onFrame).toHaveBeenCalledTimes(3);
  });

  test("processAudioChunk returns null when model is not ready", async () => {
    const { result } = renderHook(() => useVAD());
    // Don't call startVAD → session is null

    let avgProb;
    await act(async () => {
      avgProb = await result.current.processAudioChunk(makeSamples());
    });

    expect(avgProb).toBeNull();
  });

  test("stopVAD resets state; second session starts fresh", async () => {
    const session = makeSession();
    mocks.InferenceSession.create.mockResolvedValue(session);

    const { result } = renderHook(() => useVAD());

    await act(async () => {
      await result.current.startVAD(vi.fn());
    });
    expect(result.current.vadReady).toBe(true);

    act(() => {
      result.current.stopVAD();
    });

    // processAudioChunk should return null after stopVAD
    let prob;
    await act(async () => {
      prob = await result.current.processAudioChunk(makeSamples());
    });
    expect(prob).toBeNull();
  });
});
