import "@testing-library/jest-dom";
import { act, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import SubtitleBar from "../SubtitleBar";

describe("SubtitleBar", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("returns null when enabled is false", () => {
    const messages = [{ role: "user", text: "hello" }];
    const { container } = render(<SubtitleBar messages={messages} enabled={false} />);
    expect(container.firstChild).toBeNull();
  });

  test("returns null when messages is empty", () => {
    const { container } = render(<SubtitleBar messages={[]} enabled={true} />);
    expect(container.firstChild).toBeNull();
  });

  test("renders user and assistant messages with assistant persona label", () => {
    const messages = [
      { role: "user", text: "what is the time" },
      { role: "assistant", text: "It is 1:00 PM." },
    ];
    render(<SubtitleBar messages={messages} enabled={true} assistantName="E.D.I.T.H" />);

    expect(screen.getByTestId("subtitle-bar")).toBeInTheDocument();
    expect(screen.getByText("YOU ›")).toBeInTheDocument();
    expect(screen.getByText("what is the time")).toBeInTheDocument();
    expect(screen.getByText("E.D.I.T.H ›")).toBeInTheDocument();

    // Advance timers so Typewriter steps through characters
    for (let i = 0; i <= "It is 1:00 PM.".length; i++) {
      act(() => {
        vi.advanceTimersByTime(15);
      });
    }

    expect(screen.getByText("It is 1:00 PM.")).toBeInTheDocument();
  });
});
