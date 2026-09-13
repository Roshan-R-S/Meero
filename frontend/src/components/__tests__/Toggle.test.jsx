import "@testing-library/jest-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, test, vi } from "vitest";
import Toggle from "../Toggle";

describe("Toggle component", () => {
  test("renders label and toggles checked state on click", () => {
    const onChange = vi.fn();
    render(<Toggle label="Microphone Active" checked={false} onChange={onChange} />);

    const label = screen.getByText("Microphone Active");
    expect(label).toBeInTheDocument();

    const checkbox = screen.getByRole("checkbox");
    expect(checkbox).not.toBeChecked();

    fireEvent.click(checkbox);
    expect(onChange).toHaveBeenCalledWith(true);
  });

  test("shows helpText when provided", () => {
    render(
      <Toggle
        label="Wake Word"
        checked={false}
        onChange={vi.fn()}
        helpText="Requires Browser Speech Fallback"
      />
    );
    expect(screen.getByText("Requires Browser Speech Fallback")).toBeInTheDocument();
  });

  test("respects disabled prop", () => {
    const onChange = vi.fn();
    render(<Toggle label="Feature" checked={false} disabled={true} onChange={onChange} />);

    const checkbox = screen.getByRole("checkbox");
    expect(checkbox).toBeDisabled();
  });
});
