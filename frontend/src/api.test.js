import { describe, expect, test, vi } from "vitest";

describe("api config", () => {
  test("uses VITE_API_URL when provided", async () => {
    vi.resetModules();
    vi.stubEnv("VITE_API_URL", "http://api.example.test");

    const { API_URL } = await import("./api");

    expect(API_URL).toBe("http://api.example.test");
    vi.unstubAllEnvs();
  });

  test("falls back to local backend URL", async () => {
    vi.resetModules();
    vi.stubEnv("VITE_API_URL", "");

    const { API_URL } = await import("./api");

    expect(API_URL).toBe("http://localhost:8000");
    vi.unstubAllEnvs();
  });
});
