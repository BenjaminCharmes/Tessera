import { describe, it, expect } from "vitest";
import { GRILLE_COCKPIT } from "./layout";

describe("GRILLE_COCKPIT", () => {
  it("ne fixe plus de hauteur en pixels à la rangée du bas", () => {
    const rangees = GRILLE_COCKPIT.gridTemplateRows.split(" ");
    expect(rangees).toEqual(["1fr", "auto"]);
    expect(GRILLE_COCKPIT.gridTemplateRows).not.toContain("180px");
  });
});
