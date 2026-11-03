import { describe, expect, it } from "vitest";
import { LIBELLE_SANTE, santeAgent } from "./santeAgent";

const DERNIER = "2026-10-23T10:00:00.000Z";
const T0 = Date.parse(DERNIER);

describe("santeAgent", () => {
  it("is active at 29 seconds", () => {
    expect(santeAgent(DERNIER, T0 + 29_000, null)).toBe("actif");
  });

  it("is waiting at 31 seconds", () => {
    expect(santeAgent(DERNIER, T0 + 31_000, null)).toBe("attente");
  });

  it("is waiting at 179 seconds", () => {
    expect(santeAgent(DERNIER, T0 + 179_000, null)).toBe("attente");
  });

  it("suspects a stall at 181 seconds", () => {
    expect(santeAgent(DERNIER, T0 + 181_000, null)).toBe("blocage_suspecte");
  });

  it("returns question whatever the elapsed time", () => {
    for (const ecart of [5_000, 31_000, 10_000_000]) {
      expect(santeAgent(DERNIER, T0 + ecart, "On casse l'API ?")).toBe("question");
    }
  });

  it("is active without a timestamp", () => {
    expect(santeAgent(null, T0, null)).toBe("actif");
    expect(santeAgent(undefined, T0, null)).toBe("actif");
  });

  it("is active on an unreadable timestamp", () => {
    expect(santeAgent("pas une date", T0, null)).toBe("actif");
  });

  it("labels each health with its word", () => {
    expect(LIBELLE_SANTE).toEqual({
      actif: "travaille",
      attente: "silencieux",
      blocage_suspecte: "figé ?",
      question: "question",
    });
  });
});
