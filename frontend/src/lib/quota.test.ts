import { afterEach, describe, expect, it, vi } from "vitest";
import { apiQuota } from "./quota";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("apiQuota.fenetres", () => {
  it("reads the quota windows from /usage/quota", async () => {
    const corps = { windows: { five_hour: { status: "allowed", utilization: 0.4, resets_at: null, observed_at: "x" } } };
    const fetchSimule = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(corps) });
    vi.stubGlobal("fetch", fetchSimule);

    await expect(apiQuota.fenetres()).resolves.toEqual(corps);
    expect(String(fetchSimule.mock.calls[0]?.[0])).toMatch(/\/api\/v1\/usage\/quota$/);
  });

  it("rejects with the status when the API refuses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 503, statusText: "x", text: () => Promise.resolve("down") }),
    );

    await expect(apiQuota.fenetres()).rejects.toThrow("API 503: down");
  });
});
