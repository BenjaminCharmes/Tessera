import { describe, expect, it } from "vitest";
import { IMAGES_DU_CADRE, imageDuCadre } from "./cadre";

const PROJETS = ["ide-core", "alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india"];

describe("imageDuCadre", () => {
  it("gives a project the same picture on every call", () => {
    for (const projet of PROJETS) {
      expect(imageDuCadre(projet)).toBe(imageDuCadre(projet));
    }
  });

  it("stays within the pictures the frame draws", () => {
    for (const projet of PROJETS) {
      expect(imageDuCadre(projet)).toBeGreaterThanOrEqual(0);
      expect(imageDuCadre(projet)).toBeLessThan(IMAGES_DU_CADRE);
    }
  });

  it("does not give every project the same picture", () => {
    expect(new Set(PROJETS.map(imageDuCadre)).size).toBeGreaterThan(1);
  });
});
