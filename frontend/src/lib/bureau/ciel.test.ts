import { describe, expect, it } from "vitest";
import { cielDesFenetres } from "./ciel";

const MIDI = new Date(2026, 9, 27, 12).getTime();

describe("cielDesFenetres", () => {
  it("puts the sun only in the first window of the room that carries it", () => {
    expect(cielDesFenetres("directeur", 2, MIDI, true).map((c) => c.soleil)).toEqual([true, false]);
    expect(cielDesFenetres("ide-core", 2, MIDI).map((c) => c.soleil)).toEqual([false, false]);
  });

  it("draws the same clouds for the same room on the same day", () => {
    expect(cielDesFenetres("ide-core", 2, MIDI)).toEqual(cielDesFenetres("ide-core", 2, MIDI + 3_600_000));
  });

  it("never draws more than one cloud beside the sun", () => {
    for (const cle of ["a", "b", "c", "d", "e", "f", "g", "h"]) {
      const [premiere] = cielDesFenetres(cle, 2, MIDI, true);
      expect(premiere?.nuages).toBeLessThanOrEqual(1);
    }
  });
});
