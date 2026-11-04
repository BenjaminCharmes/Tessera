import { describe, expect, it, vi } from "vitest";
import { planDeNettoyage, serviceActif } from "./exemples";

// Le client est remplacé comme le font les tests de composant : `vi.mock` sans
// fabrique, puis `vi.mocked` à la racine du fichier (ticket-765).
vi.mock("../../lib/api");
import { api } from "../../lib/api";

const plan = vi.mocked(api.git.cleanupPlan);
const lister = vi.mocked(api.services.list);

describe("contract guard on responses posed through vi.mocked", () => {
  it("refuses a value the schema does not describe, as vi.spyOn does", () => {
    expect(() => plan.mockResolvedValue({ nettoyables: "x" } as never)).toThrow(/branches\/cleanup/);
    expect(() => lister.mockResolvedValueOnce({ services: [] } as never)).toThrow(/GET .*\/services/);
  });

  it("names the field that is missing", () => {
    expect(() => lister.mockResolvedValue([{ nom: "back" }] as never)).toThrow(/champ requis absent/);
  });

  it("lets a conforming value through and returns it", async () => {
    plan.mockResolvedValue(planDeNettoyage({ nettoyables: ["ticket-001-x"] }));
    lister.mockResolvedValue([serviceActif({ nom: "back" })]);

    await expect(api.git.cleanupPlan("p")).resolves.toEqual({ nettoyables: ["ticket-001-x"], conservees: [] });
    await expect(api.services.list("p")).resolves.toHaveLength(1);
  });

  it("leaves a function outside the perimeter alone", () => {
    const statuts = vi.mocked(api.github.getPrStatuses);

    expect(() => statuts.mockResolvedValue([])).not.toThrow();
  });
});
