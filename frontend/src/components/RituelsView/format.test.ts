import { describe, expect, it } from "vitest";

import { libelleDuRythme } from "./format";

describe("libelleDuRythme", () => {
  it("renders a daily rhythm", () => {
    expect(libelleDuRythme({ type: "quotidien", heure: "18:00", jours: "tous" })).toBe(
      "Chaque jour à 18:00",
    );
  });

  it("renders a daily rhythm on working days", () => {
    expect(libelleDuRythme({ type: "quotidien", heure: "18:00", jours: "ouvres" })).toBe(
      "Chaque jour ouvré à 18:00",
    );
  });
});
