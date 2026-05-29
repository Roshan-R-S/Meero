import { afterEach, describe, expect, test, vi } from "vitest";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
});

describe("logger", () => {
  test("does not write debug logs outside dev mode", async () => {
    vi.resetModules();
    vi.stubEnv("DEV", false);
    const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    const { logger } = await import("./logger");
    logger.log("hidden");

    expect(logSpy).not.toHaveBeenCalled();
  });

  test("keeps error logging available", async () => {
    vi.resetModules();
    vi.stubEnv("DEV", false);
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    const { logger } = await import("./logger");
    logger.error("visible");

    expect(errorSpy).toHaveBeenCalledWith("visible");
  });
});
