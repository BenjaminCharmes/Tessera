import { describe, expect, it } from "vitest";
import { couleurDuBudget, resumeDuCout } from "./budget";

describe("couleurDuBudget", () => {
  it("passe en amber a 70 % et en red a 90 % du plafond", () => {
    expect(couleurDuBudget(3.4, 5)).toBe("zinc");
    expect(couleurDuBudget(3.5, 5)).toBe("amber");
    expect(couleurDuBudget(4.5, 5)).toBe("red");
  });

  it("reste neutre sans plafond", () => {
    // Un plafond a zero ne borne rien (ADR-020) : rien a signaler.
    expect(couleurDuBudget(12, 0)).toBe("zinc");
    expect(couleurDuBudget(12, null)).toBe("zinc");
  });
});

describe("resumeDuCout", () => {
  it("dit le cout, les appels, les outils et le plafond", () => {
    expect(resumeDuCout(0.84, 3, 47, 5)).toBe("0,84 $ · 3 appels · 47 outils sur 5,00 $");
    expect(resumeDuCout(0.1, 1, 1)).toBe("0,10 $ · 1 appel · 1 outil");
  });
});
