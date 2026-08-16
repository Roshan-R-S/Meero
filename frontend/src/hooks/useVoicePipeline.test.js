import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import useVoicePipeline from "./useVoicePipeline";

const mocks = vi.hoisted(() => ({
  sendVoiceCommand: vi.fn(),
  recorder: {
    supported: true,
    recording: false,
    micEnergyLevel: 0,
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
    cancelRecording: vi.fn(),
  },
  vad: {
    vadReady: true,
    startVAD: vi.fn().mockResolvedValue(undefined),
    stopVAD: vi.fn(),
    processAudioChunk: vi.fn().mockResolvedValue(0.8),
  },
}));

vi.mock("../api", () => ({
  sendVoiceCommand: mocks.sendVoiceCommand,
}));

vi.mock("./useAudioRecorder", () => ({
  default: () => mocks.recorder,
}));

vi.mock("./useVAD", () => ({
  default: () => mocks.vad,
}));

let audioInstances;
let originalAudio;

class MockAudio {
  constructor(source) {
    this.source = source;
    this.play = vi.fn().mockResolvedValue(undefined);
    audioInstances.push(this);
  }
}

describe("useVoicePipeline", () => {
  beforeEach(() => {
    originalAudio = globalThis.Audio;
    globalThis.Audio = MockAudio;
    audioInstances = [];
    mocks.recorder.recording = false;
    mocks.recorder.micEnergyLevel = 0;
    mocks.recorder.startRecording.mockReset();
    mocks.recorder.stopRecording.mockReset();
    mocks.recorder.cancelRecording.mockReset();
    mocks.vad.startVAD.mockReset().mockResolvedValue(undefined);
    mocks.vad.stopVAD.mockReset();
    mocks.vad.processAudioChunk.mockReset().mockResolvedValue(0.8);
    mocks.sendVoiceCommand.mockReset();
  });

  afterEach(() => {
    globalThis.Audio = originalAudio;
    vi.clearAllMocks();
  });

  test("submits auto-stopped audio, delivers the result, and plays returned audio", async () => {
    const audio = new Blob(["wav"], { type: "audio/wav" });
    const response = {
      response: "Done.",
      audio_base64: "UklGRg==",
      audio_mime_type: "audio/wav",
    };
    const onResult = vi.fn();
    const setState = vi.fn();
    mocks.sendVoiceCommand.mockResolvedValue(response);
    mocks.recorder.startRecording.mockImplementation(async ({ onStop }) => {
      await onStop(audio);
    });
    const { result } = renderHook(() =>
      useVoicePipeline({
        onResult,
        pendingCommand: "close calculator",
        setState,
      }),
    );

    await act(async () => {
      await result.current.toggleRecording();
    });

    expect(mocks.sendVoiceCommand).toHaveBeenCalledWith(audio, {
      pendingCommand: "close calculator",
    });
    expect(onResult).toHaveBeenCalledWith(response);
    expect(setState).toHaveBeenCalledWith("speaking");
    expect(audioInstances[0].source).toBe("data:audio/wav;base64,UklGRg==");
    expect(audioInstances[0].play).toHaveBeenCalledOnce();
    expect(result.current.processing).toBe(false);

    await act(async () => {
      audioInstances[0].onended();
      await Promise.resolve();
    });
    expect(setState).toHaveBeenLastCalledWith("idle");
  });

  test("starts VAD session before starting the recorder when vadReady", async () => {
    mocks.recorder.startRecording.mockResolvedValue(undefined);
    const { result } = renderHook(() =>
      useVoicePipeline({ onResult: vi.fn(), setState: vi.fn() }),
    );

    await act(async () => {
      await result.current.toggleRecording();
    });

    expect(mocks.vad.startVAD).toHaveBeenCalledOnce();
    expect(mocks.recorder.startRecording).toHaveBeenCalledWith(
      expect.objectContaining({
        processAudioChunk: mocks.vad.processAudioChunk,
      }),
    );
  });

  test("passes undefined processAudioChunk to recorder when VAD is not ready", async () => {
    // Override VAD to be not ready for this test
    mocks.vad.vadReady = false;
    mocks.recorder.startRecording.mockResolvedValue(undefined);

    const { result } = renderHook(() =>
      useVoicePipeline({ onResult: vi.fn(), setState: vi.fn() }),
    );

    await act(async () => {
      await result.current.toggleRecording();
    });

    // recorder should be called without VAD integration
    const callArgs = mocks.recorder.startRecording.mock.calls[0][0];
    expect(callArgs.processAudioChunk).toBeUndefined();
    expect(callArgs.onVADFrame).toBeUndefined();

    // Restore for other tests
    mocks.vad.vadReady = true;
  });

  test("submits manually stopped audio without entering speaking state when audio is absent", async () => {
    const audio = new Blob(["wav"], { type: "audio/wav" });
    const setState = vi.fn();
    mocks.recorder.recording = true;
    mocks.recorder.stopRecording.mockResolvedValue(audio);
    mocks.sendVoiceCommand.mockResolvedValue({ response: "Done.", audio_base64: null });
    const { result } = renderHook(() =>
      useVoicePipeline({ onResult: vi.fn(), setState }),
    );

    await act(async () => {
      await result.current.toggleRecording();
    });

    expect(mocks.recorder.stopRecording).toHaveBeenCalledOnce();
    expect(mocks.sendVoiceCommand).toHaveBeenCalledWith(audio, {
      pendingCommand: undefined,
    });
    expect(setState).not.toHaveBeenCalled();
    expect(result.current.processing).toBe(false);
  });

  test("exposes vadReady from the VAD hook", () => {
    const { result } = renderHook(() =>
      useVoicePipeline({ onResult: vi.fn(), setState: vi.fn() }),
    );
    expect(result.current.vadReady).toBe(true);
  });

  test("exposes a stable local voice error", async () => {
    mocks.recorder.startRecording.mockRejectedValue(
      new Error("Local voice processing failed."),
    );
    const { result } = renderHook(() =>
      useVoicePipeline({ onResult: vi.fn(), setState: vi.fn() }),
    );

    await act(async () => {
      await result.current.toggleRecording();
    });

    expect(result.current.error).toBe("Local voice processing failed.");
    expect(result.current.processing).toBe(false);
  });
});
