import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import useSpeechRecognition from "./useSpeechRecognition";

vi.mock("../utils/sound", () => ({
  playListeningStart: vi.fn(),
  playListeningStop: vi.fn(),
}));

let recognition;

class MockSpeechRecognition {
  constructor() {
    this.start = vi.fn();
    this.abort = vi.fn();
    recognition = this;
  }
}

const emitResult = (transcript) => {
  act(() => {
    recognition.onresult({
      results: [[{ transcript }]],
    });
  });
};

describe("useSpeechRecognition", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    window.SpeechRecognition = MockSpeechRecognition;
  });

  afterEach(() => {
    delete window.SpeechRecognition;
    recognition = null;
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  test.each(["hey miro", "hey mirror", "hey nero"])(
    "handles the %s wake-word variant with an inline command",
    (wakeVariant) => {
      const onResult = vi.fn();
      const setState = vi.fn();
      const onInterrupt = vi.fn();
      const { result } = renderHook(() =>
        useSpeechRecognition(onResult, "idle", setState, onInterrupt),
      );

      act(() => result.current.setWakeWordEnabled(true));
      act(() => vi.advanceTimersByTime(250));
      emitResult(`${wakeVariant} open calculator`);

      expect(onInterrupt).toHaveBeenCalledOnce();
      expect(recognition.abort).toHaveBeenCalled();
      expect(setState).toHaveBeenCalledWith("processing");
      expect(onResult).toHaveBeenCalledWith("open calculator");
    },
  );

  test("moves from passive wake scanning to active command listening", () => {
    const onResult = vi.fn();
    const setState = vi.fn();
    const { result } = renderHook(() =>
      useSpeechRecognition(onResult, "idle", setState),
    );

    act(() => result.current.setWakeWordEnabled(true));
    emitResult("hey meero");

    expect(setState).toHaveBeenCalledWith("listening");
    expect(onResult).not.toHaveBeenCalled();

    emitResult("what time is it");

    expect(onResult).toHaveBeenCalledWith("what time is it");
    expect(recognition.abort).toHaveBeenCalled();
    expect(setState).toHaveBeenCalledWith("processing");
  });

  test("submits manual push-to-talk results", () => {
    const onResult = vi.fn();
    const { result } = renderHook(() =>
      useSpeechRecognition(onResult, "idle", vi.fn()),
    );

    act(() => result.current.toggleListen());
    act(() => vi.advanceTimersByTime(200));
    emitResult("What Time Is It?");

    expect(recognition.abort).toHaveBeenCalled();
    expect(onResult).toHaveBeenCalledWith("what time is it");
    expect(result.current.isConversingRef.current).toBe(false);
  });

  test("reports microphone permission errors", () => {
    const setState = vi.fn();
    const { result } = renderHook(() =>
      useSpeechRecognition(vi.fn(), "idle", setState),
    );

    act(() => {
      recognition.onerror({ error: "not-allowed" });
    });

    expect(result.current.recognitionError).toBe("Microphone permission denied.");
    expect(setState).toHaveBeenCalledWith("idle");
  });
});
