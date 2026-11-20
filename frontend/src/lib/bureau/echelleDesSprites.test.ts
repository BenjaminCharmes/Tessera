import { describe, expect, it } from "vitest";
import {
  ECHELLE_DU_MOBILIER,
  ECHELLE_LARGE,
  ECHELLE_MIN,
  FACTEUR_DE_LA_PIECE,
  echelleDeLaPiece,
  echellePourLargeur,
} from "./echelleDesSprites";

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

describe("narrow screens", () => {
  it("shrinks the sprites enough at 1280 px for the four top rooms to hold their wall and floor", () => {
    // À 0,9, la fenêtre, l'interrupteur et le canapé sortaient des salles du haut (ticket-727).
    expect(echellePourLargeur(1280)).toBeLessThanOrEqual(0.7);
    expect(echellePourLargeur(1536)).toBe(0.95);
    expect(echellePourLargeur(1920)).toBeGreaterThan(echellePourLargeur(1536));
  });
});

describe("ECHELLE_DU_MOBILIER", () => {
  it("draws furniture a fifth larger than the characters", () => {
    expect(ECHELLE_DU_MOBILIER).toBeGreaterThanOrEqual(1.2);
    expect(ECHELLE_DU_MOBILIER).toBeLessThanOrEqual(1.25);
  });
});

describe("echelleDeLaPiece", () => {
  it("draws the run room larger than the top rooms on a laptop", () => {
    const commune = echellePourLargeur(1536);
    expect(echelleDeLaPiece(commune)).toBeGreaterThan(commune);
    expect(echelleDeLaPiece(commune)).toBe(1.1);
  });

  it("never goes beyond the wide-screen scale", () => {
    expect(echelleDeLaPiece(ECHELLE_LARGE)).toBe(ECHELLE_LARGE);
    expect(echelleDeLaPiece(echellePourLargeur(1920))).toBe(ECHELLE_LARGE);
  });

  it("multiplies the shared scale and moves by twentieths", () => {
    expect(echelleDeLaPiece(ECHELLE_MIN)).toBe(Math.floor(ECHELLE_MIN * FACTEUR_DE_LA_PIECE * 20 + 1e-9) / 20);
    expect((echelleDeLaPiece(0.85) * 20) % 1).toBe(0);
  });
});
