import { describe, expect, it } from "vitest";
import { transitionPermise, transitionsManuelles } from "./transitionsManuelles";

describe("transitionsManuelles", () => {
  it("ne propose jamais in-progress ni in-review", () => {
    // Ces statuts sont tenus par le pipeline : un ticket in-progress sans run
    // se lirait comme un run fantome (ticket-177).
    for (const depuis of ["todo", "blocked", "done", "cancelled"] as const) {
      expect(transitionsManuelles(depuis)).not.toContain("in-progress");
      expect(transitionsManuelles(depuis)).not.toContain("in-review");
    }
  });

  it("n'offre rien depuis un statut tenu par le pipeline", () => {
    expect(transitionsManuelles("in-progress")).toEqual([]);
    expect(transitionsManuelles("in-review")).toEqual([]);
  });

  it("remet un ticket bloque ou clos dans la file", () => {
    expect(transitionPermise("blocked", "todo")).toBe(true);
    expect(transitionPermise("done", "todo")).toBe(true);
    expect(transitionPermise("cancelled", "todo")).toBe(true);
  });

  it("refuse une transition hors de la table", () => {
    expect(transitionPermise("todo", "in-review")).toBe(false);
    expect(transitionPermise("done", "cancelled")).toBe(false);
  });
});
