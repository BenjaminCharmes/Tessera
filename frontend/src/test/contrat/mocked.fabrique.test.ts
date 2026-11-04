import { describe, expect, it, vi } from "vitest";

// Une fabrique qui n'expose qu'une partie du client, comme `ProjetCarte.test.tsx`.
vi.mock("../../lib/api", () => ({
  api: { services: { start: vi.fn(), stop: vi.fn() } },
}));
import { api } from "../../lib/api";

const demarrer = vi.mocked(api.services.start);

describe("contract guard on a mock built by a factory", () => {
  it("refuses a response that is not the one of services/start", () => {
    expect(() => demarrer.mockResolvedValue([] as never)).toThrow(/POST .*services\/start/);
  });

  it("accepts the response the route sends", async () => {
    demarrer.mockResolvedValue({ services: [] });

    await expect(api.services.start("p")).resolves.toEqual({ services: [] });
  });
});
