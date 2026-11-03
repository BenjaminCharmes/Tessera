import { describe, expect, it } from "vitest";
import { depart } from "./confettis";

describe("Confettis", () => {
  it("spreads the confetti across the whole room width, in percent", () => {
    const abscisses = Array.from({ length: 18 }, (_, i) =>
      parseFloat(depart(i).left),
    );

    expect(depart(0).left.endsWith("%")).toBe(true);
    expect(Math.min(...abscisses)).toBeLessThan(15);
    expect(Math.max(...abscisses)).toBeGreaterThan(85);
  });
});
