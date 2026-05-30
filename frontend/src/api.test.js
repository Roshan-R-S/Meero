import { afterEach, describe, expect, test, vi } from "vitest";

afterEach(() => {
  vi.resetModules();
  vi.unstubAllEnvs();
  vi.doUnmock("axios");
});

describe("api config", () => {
  test("uses VITE_API_URL when provided", async () => {
    vi.resetModules();
    vi.stubEnv("VITE_API_URL", "http://api.example.test");

    const { API_URL } = await import("./api");

    expect(API_URL).toBe("http://api.example.test");
  });

  test("falls back to local backend URL", async () => {
    vi.resetModules();
    vi.stubEnv("VITE_API_URL", "");

    const { API_URL } = await import("./api");

    expect(API_URL).toBe("http://localhost:8000");
  });

  test("sends API key header when configured", async () => {
    const post = vi.fn().mockResolvedValue({ data: { response: "ok" } });
    vi.stubEnv("VITE_MEERO_API_KEY", "secret-key");
    vi.doMock("axios", () => ({
      default: { post },
    }));

    const { sendCommand } = await import("./api");
    await sendCommand("hello");

    expect(post).toHaveBeenCalledWith(
      "http://localhost:8000/command",
      {
        command: "hello",
        mode: "voice",
        confirm: false,
        pending_command: null,
      },
      { headers: { "x-meero-api-key": "secret-key" } },
    );
  });

  test("omits API key header when not configured", async () => {
    const post = vi.fn().mockResolvedValue({ data: { response: "ok" } });
    vi.stubEnv("VITE_MEERO_API_KEY", "");
    vi.doMock("axios", () => ({
      default: { post },
    }));

    const { sendCommand } = await import("./api");
    await sendCommand("hello");

    expect(post).toHaveBeenCalledWith(
      "http://localhost:8000/command",
      {
        command: "hello",
        mode: "voice",
        confirm: false,
        pending_command: null,
      },
      { headers: {} },
    );
  });
});
