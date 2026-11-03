import { afterEach, describe, expect, it, vi } from "vitest";
import { apiVentilation } from "./ventilation";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("apiVentilation.parProjet", () => {
  it("reads the project's cost by role from /usage/breakdown", async () => {
    const corps = { per_agent: [{ role: "codeur", total_cost_usd: 1, total_tokens: 2, call_count: 3 }] };
    const fetchSimule = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(corps) });
    vi.stubGlobal("fetch", fetchSimule);

    await expect(apiVentilation.parProjet("ide-core")).resolves.toEqual(corps);
    expect(String(fetchSimule.mock.calls[0]?.[0])).toMatch(/\/api\/v1\/projects\/ide-core\/usage\/breakdown$/);
  });

  it("rejects with the status when the API refuses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 500, statusText: "x", text: () => Promise.resolve("boom") }),
    );

    await expect(apiVentilation.parProjet("ide-core")).rejects.toThrow("API 500: boom");
  });
});
