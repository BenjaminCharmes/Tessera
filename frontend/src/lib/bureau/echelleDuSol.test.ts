import { describe, expect, it } from "vitest";
import { echelleDuSol } from "./echelleDuSol";

describe("echelleDuSol", () => {
  it("keeps the logical scale at 800 px", () => {
    expect(echelleDuSol(800)).toBe(1);
  });

  it("grows the floor in proportion to the width", () => {
    expect(echelleDuSol(1200)).toBe(1.5);
  });

  it("stops shrinking at the lower bound", () => {
    expect(echelleDuSol(300)).toBe(0.5);
  });

  it("stops growing at the upper bound", () => {
    expect(echelleDuSol(2400)).toBe(2);
  });

  it("falls back to the logical scale on a width it cannot read", () => {
    expect(echelleDuSol(Number.NaN)).toBe(1);
  });
});
