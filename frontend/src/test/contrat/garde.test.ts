import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../../lib/api";
import { apiQuota } from "../../lib/quota";
import { statutsDuRun } from "../../lib/statutDuRun";
import { fenetresDeQuota, planDeNettoyage, serviceActif, statutDuRun, ventilation } from "./exemples";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("contract guard on mocked responses", () => {
  it("refuses an array where the schema describes an object", () => {
    const demarrer = vi.spyOn(api.services, "start");

    expect(() => demarrer.mockResolvedValue([] as never)).toThrow(/POST .*services\/start/);
  });

  it("refuses an object where the schema describes an array", () => {
    const lister = vi.spyOn(api.services, "list");

    expect(() => lister.mockResolvedValue({ services: [] } as never)).toThrow(/GET .*\/services/);
  });

  it("refuses a field the schema does not know and one it requires", () => {
    const lire = vi.spyOn(statutsDuRun, "lire");

    expect(() => lire.mockResolvedValue({ ...statutDuRun(), invente: 1 } as never)).toThrow(/invente/);
    expect(() => lire.mockResolvedValueOnce({ project_id: "p" } as never)).toThrow(/champ requis absent/);
  });

  it("lets a conforming value through and returns it", async () => {
    vi.spyOn(apiQuota, "fenetres").mockResolvedValue(fenetresDeQuota());
    vi.spyOn(api.services, "list").mockResolvedValue([serviceActif({ nom: "back" })]);

    await expect(apiQuota.fenetres()).resolves.toEqual({ windows: {} });
    await expect(api.services.list("p")).resolves.toHaveLength(1);
  });

  it("leaves a function outside the perimeter alone", () => {
    const lire = vi.spyOn(api.github, "getPrStatuses");

    expect(() => lire.mockResolvedValue([])).not.toThrow();
  });
});

describe("fixtures drawn from the schema", () => {
  it("builds an object that carries every field of the response", () => {
    expect(Object.keys(statutDuRun()).sort()).toEqual(
      ["approuves", "arretes", "debut", "faits", "fin", "mode", "project_id", "restants", "statut", "ticket_courant"],
    );
  });

  it("accepts the stopped tickets the front used to ignore", () => {
    const statut = statutDuRun({ arretes: [{ ticket_id: "ticket-002", motif: null }] });

    expect(statut.arretes[0].ticket_id).toBe("ticket-002");
  });

  it("refuses an override of the wrong type", () => {
    expect(() => ventilation({ total_cost_usd: "12" as never })).toThrow(/non conforme/);
    expect(() => planDeNettoyage({ nettoyables: "x" as never })).toThrow(/non conforme/);
  });
});
