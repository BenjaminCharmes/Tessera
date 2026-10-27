import { describe, expect, it } from "vitest";
import { enPourcentDuSol, etirementDuSol } from "./etirementDuSol";

describe("etirementDuSol", () => {
  it("stretches the 800 px frame over the room's width, without an upper bound", () => {
    expect(etirementDuSol(800)).toBe(1);
    expect(etirementDuSol(1200)).toBe(1.5);
    expect(etirementDuSol(2400)).toBe(3);
  });

  it("never squeezes below 0.75, where the desks would overlap", () => {
    expect(etirementDuSol(300)).toBe(0.75);
  });

  it("keeps 1 for a width that is not a measure", () => {
    expect(etirementDuSol(0)).toBe(1);
    expect(etirementDuSol(Number.NaN)).toBe(1);
  });
});

describe("enPourcentDuSol", () => {
  it("turns an abscissa of the 800 px frame into a share of the floor", () => {
    expect(enPourcentDuSol(400)).toBe("50%");
    expect(enPourcentDuSol(0)).toBe("0%");
  });
});
