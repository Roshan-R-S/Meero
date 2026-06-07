import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import useSpeechSynthesis from "./useSpeechSynthesis";

let spokenUtterance;

class MockSpeechSynthesisUtterance {
  constructor(text) {
    this.text = text;
  }
}

describe("useSpeechSynthesis", () => {
  beforeEach(() => {
    spokenUtterance = null;
    window.speechSynthesis = {
      speaking: false,
      cancel: vi.fn(),
      getVoices: vi.fn(() => []),
      speak: vi.fn((utterance) => {
        spokenUtterance = utterance;
      }),
    };
    window.SpeechSynthesisUtterance = MockSpeechSynthesisUtterance;
    globalThis.SpeechSynthesisUtterance = MockSpeechSynthesisUtterance;
  });

  afterEach(() => {
    delete window.speechSynthesis;
    delete window.SpeechSynthesisUtterance;
    delete globalThis.SpeechSynthesisUtterance;
    vi.clearAllMocks();
  });

  test("calls the recognition-restart callback after speech completes", () => {
    const setState = vi.fn();
    const restartRecognition = vi.fn();
    const { result } = renderHook(() =>
      useSpeechSynthesis(setState, restartRecognition),
    );

    act(() => result.current.speak("Ready."));
    act(() => spokenUtterance.onend());

    expect(setState).toHaveBeenCalledWith("speaking");
    expect(setState).toHaveBeenCalledWith("idle");
    expect(restartRecognition).toHaveBeenCalledOnce();
  });
});
