import "@testing-library/jest-dom";
import { act, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { sendCommand } from "./api";
import App from "./App";

vi.mock("./api", () => ({
  sendCommand: vi.fn(),
}));

vi.mock("./components/Background", () => ({
  default: () => <div data-testid="background" />,
}));

vi.mock("./components/HologramOverlay", () => ({
  default: () => <div data-testid="hologram" />,
}));

vi.mock("./components/ThreeOrb", () => ({
  default: () => <div data-testid="three-orb" />,
}));

vi.mock("./utils/sound", () => ({
  playProcessing: vi.fn(),
  playStartup: vi.fn(),
}));

vi.mock("./hooks/useSpeechRecognition", () => ({
  default: vi.fn(() => ({
    isConversing: false,
    isConversingRef: { current: false },
    toggleListen: vi.fn(),
    recognitionRef: { current: { start: vi.fn() } },
    wakeWordEnabled: false,
    setWakeWordEnabled: vi.fn(),
    startActiveListening: vi.fn(),
    recognitionError: "",
  })),
}));

vi.mock("./hooks/useSpeechSynthesis", () => ({
  default: vi.fn(() => ({
    speak: vi.fn(),
  })),
}));

describe("App typed fallback", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    sendCommand.mockResolvedValue({
      response: "Done.",
      action_status: "success",
      sentiment: "neutral",
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  test("shows typed command fallback when speech recognition is unavailable", () => {
    render(<App />);

    act(() => {
      vi.advanceTimersByTime(3500);
    });

    expect(screen.getByLabelText("Type command")).toBeInTheDocument();
    expect(screen.getByText(/Speech recognition is not available/i)).toBeInTheDocument();
  });

  test("submits typed commands through the existing command API", async () => {
    render(<App />);

    act(() => {
      vi.advanceTimersByTime(3500);
    });

    fireEvent.change(screen.getByLabelText("Type command"), {
      target: { value: "what time is it" },
    });
    await act(async () => {
      fireEvent.click(screen.getByLabelText("Send command"));
      await Promise.resolve();
    });

    expect(sendCommand).toHaveBeenCalledWith("what time is it");
  });
});
