import "@testing-library/jest-dom";
import { act, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { getHealth, getSettings, saveSettings, sendCommand } from "./api";
import App from "./App";

vi.mock("./api", () => ({
  getHealth: vi.fn(),
  getSettings: vi.fn(),
  saveSettings: vi.fn(),
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
    getHealth.mockResolvedValue({
      status: "ok",
      web_safe_mode: true,
    });
    getSettings.mockResolvedValue({});
    saveSettings.mockResolvedValue({ status: "ok" });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  test("shows typed command fallback when speech recognition is unavailable", async () => {
    render(<App />);

    await act(async () => {
      vi.advanceTimersByTime(3500);
      await Promise.resolve();
    });

    expect(screen.getByLabelText("Type command")).toBeInTheDocument();
    expect(screen.getByText(/Speech recognition is not available/i)).toBeInTheDocument();
  });

  test("submits typed commands through the existing command API", async () => {
    render(<App />);

    await act(async () => {
      vi.advanceTimersByTime(3500);
      await Promise.resolve();
    });

    fireEvent.change(screen.getByLabelText("Type command"), {
      target: { value: "what time is it" },
    });
    await act(async () => {
      fireEvent.click(screen.getByLabelText("Send command"));
      await Promise.resolve();
    });

    expect(sendCommand).toHaveBeenCalledWith("what time is it");
    expect(screen.getByText("user:")).toBeInTheDocument();
    expect(screen.getByText("what time is it")).toBeInTheDocument();
    expect(screen.getAllByText("Done.").length).toBeGreaterThan(0);
  });

  test("opens settings panel and saves supported settings", async () => {
    render(<App />);

    await act(async () => {
      vi.advanceTimersByTime(3500);
      await Promise.resolve();
    });

    fireEvent.click(screen.getByLabelText("Open settings"));
    expect(screen.getByText("Settings")).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByText("Save"));
      await Promise.resolve();
    });

    expect(saveSettings).toHaveBeenCalledWith({
      wake_word_enabled: false,
      voice_rate: 1,
      voice_pitch: 1,
    });
  });
});
