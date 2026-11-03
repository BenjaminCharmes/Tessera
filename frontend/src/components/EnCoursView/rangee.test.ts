import { describe, expect, it } from "vitest";
import type { AgentDuService } from "./AgentsDeProduit";
import { capaciteDeLaRangee, rangee } from "./rangee";

function agent(id: string, etat: "actif" | "repos"): AgentDuService {
  return { service: "worker", agent: { id, nom: id, etat, depuis: null, libelle: null } };
}

describe("capaciteDeLaRangee", () => {
  it("counts the desks that fit, gaps included", () => {
    expect(capaciteDeLaRangee(1000, 100, 25)).toBe(8);
    expect(capaciteDeLaRangee(99, 100, 25)).toBe(1);
  });

  it("keeps at least one desk when the width is unknown", () => {
    expect(capaciteDeLaRangee(0, 100, 25)).toBe(1);
    expect(capaciteDeLaRangee(Number.NaN, 100, 25)).toBe(1);
  });
});

describe("rangee", () => {
  it("draws every agent when they fit, busy ones first", () => {
    const r = rangee([agent("a", "repos"), agent("b", "actif"), agent("c", "repos")], 5);
    expect(r.visibles.map((a) => a.agent.id)).toEqual(["b", "a", "c"]);
    expect(r.enPlus).toBe(0);
  });

  it("gives the last desk to a +N badge when there are too many", () => {
    const agents = ["a", "b", "c", "d", "e"].map((id) => agent(id, "repos"));
    const r = rangee(agents, 3);
    expect(r.visibles.map((a) => a.agent.id)).toEqual(["a", "b"]);
    expect(r.enPlus).toBe(3);
  });

  it("never hides a busy agent behind a resting one", () => {
    const r = rangee([agent("a", "repos"), agent("b", "repos"), agent("c", "actif")], 2);
    expect(r.visibles.map((a) => a.agent.id)).toEqual(["c"]);
  });
});
