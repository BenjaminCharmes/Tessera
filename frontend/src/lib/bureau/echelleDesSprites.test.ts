import { describe, expect, it } from "vitest";
import { ECHELLE_LARGE, ECHELLE_MIN, echellePourLargeur } from "./echelleDesSprites";

describe("echellePourLargeur", () => {
  it("keeps the full scale on a wide screen", () => {
    expect(echellePourLargeur(2200)).toBe(ECHELLE_LARGE);
    expect(echellePourLargeur(Infinity)).toBe(ECHELLE_LARGE);
  });

  it("shrinks the sprites on a laptop so the four rooms still fit side by side", () => {
    const echelle = echellePourLargeur(1536);
    expect(echelle).toBeLessThan(ECHELLE_LARGE);
    expect(echelle).toBeGreaterThanOrEqual(ECHELLE_MIN);
    expect((((1536 - 430) / 4 - 48) / echelle) >= 240).toBe(true);
  });

  it("never goes below the readable floor", () => {
    expect(echellePourLargeur(900)).toBe(ECHELLE_MIN);
  });

  it("moves by twentieths, not by pixels", () => {
    expect((echellePourLargeur(1600) * 20) % 1).toBe(0);
  });
});
