import "@testing-library/jest-dom";
import { act, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { getHealth, getSettings, saveSettings, sendCommand, getModelStatus } from "./api";
import App from "./App";

vi.mock("./api", () => ({
  getHealth: vi.fn(),
  getSettings: vi.fn(),
  saveSettings: vi.fn(),
  sendCommand: vi.fn(),
  getModelStatus: vi.fn(),
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

const renderApp = async () => {
  let rendered;
  await act(async () => {
    rendered = render(<App />);
    await Promise.resolve();
    await Promise.resolve();
  });
  return rendered;
};

const finishBoot = async () => {
  await act(async () => {
    vi.advanceTimersByTime(3500);
    await Promise.resolve();
    await Promise.resolve();
  });
};

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
      detailed: true,
      web_safe_mode: true,
    });
    getSettings.mockResolvedValue({
      text_input_enabled: true,
      show_history: true,
    });
    saveSettings.mockResolvedValue({ status: "ok" });
    getModelStatus.mockResolvedValue({
      neural_net: { enabled: true, loaded: true },
      gguf_llm: { enabled: true, loaded: true },
    });
    window.localStorage?.removeItem?.("meero.messages");
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  test("shows typed command fallback when speech recognition is unavailable", async () => {
    await renderApp();
    await finishBoot();

    expect(screen.getByLabelText("Type command")).toBeInTheDocument();
    expect(screen.getByText(/Speech recognition is not available/i)).toBeInTheDocument();
  });

  test("submits typed commands through the existing command API", async () => {
    await renderApp();
    await finishBoot();

    await act(async () => {
      fireEvent.change(screen.getByLabelText("Type command"), {
        target: { value: "what time is it" },
      });
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
    await renderApp();
    await finishBoot();

    await act(async () => {
      fireEvent.click(screen.getByLabelText("Open settings"));
    });
    expect(screen.getByText("Settings")).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByText("Save"));
      await Promise.resolve();
    });

    expect(saveSettings).toHaveBeenCalledWith({
      wake_word_enabled: false,
      voice_rate: 1,
      voice_pitch: 1,
      show_history: true,
      text_input_enabled: true,
    });
  });

  test("shows limited status when only public health is available", async () => {
    getHealth.mockResolvedValue({
      status: "ok",
      detailed: false,
    });

    await renderApp();
    await finishBoot();

    await act(async () => {
      fireEvent.click(screen.getByLabelText("Open settings"));
    });

    expect(screen.getByText(/API: online/i)).toBeInTheDocument();
    expect(screen.getByText(/Desktop: unknown/i)).toBeInTheDocument();
  });

  test("refreshes API status from settings", async () => {
    await renderApp();
    await finishBoot();

    await act(async () => {
      fireEvent.click(screen.getByLabelText("Open settings"));
    });
    getHealth.mockClear();

    await act(async () => {
      fireEvent.click(screen.getByLabelText("Refresh API status"));
      await Promise.resolve();
    });

    expect(getHealth).toHaveBeenCalledTimes(1);
  });

  test("copies and clears conversation history", async () => {
    await renderApp();
    await finishBoot();

    await act(async () => {
      fireEvent.change(screen.getByLabelText("Type command"), {
        target: { value: "what time is it" },
      });
    });
    await act(async () => {
      fireEvent.click(screen.getByLabelText("Send command"));
      await Promise.resolve();
    });

    await act(async () => {
      fireEvent.click(screen.getByLabelText(/Copy assistant response/i));
      await Promise.resolve();
    });

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("Done.");

    await act(async () => {
      fireEvent.click(screen.getByLabelText("Clear conversation history"));
    });

    expect(screen.queryByText("what time is it")).not.toBeInTheDocument();
  });

});
