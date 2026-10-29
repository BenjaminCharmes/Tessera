import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import type { EcranId } from "../../lib/bureau/ecranDuPoste";
import Ecran from "./Ecran";

const SCENES: EcranId[] = ["code", "lecture", "tests", "audit", "diff", "criteres", "ok", "ko"];

function dessiner(ecran: EcranId, anime: boolean): Element {
  const { container } = render(
    <svg>
      <Ecran ecran={ecran} ton={anime ? "actif" : "attente"} anime={anime} />
    </svg>,
  );
  const dessin = container.querySelector('[data-sprite="ecran"]');
  if (dessin === null) throw new Error("no screen drawn");
  return dessin;
}

function classes(dessin: Element): string[] {
  return [...dessin.querySelectorAll("[class]")].flatMap((e) => (e.getAttribute("class") ?? "").split(/\s+/));
}

describe("Ecran", () => {
  it("carries its scene in data-ecran and draws it clipped to the lit area", () => {
    for (const ecran of SCENES) {
      const dessin = dessiner(ecran, true);
      expect(dessin.getAttribute("data-ecran"), ecran).toBe(ecran);
      expect(dessin.querySelector("svg"), ecran).not.toBeNull();
    }
  });

  it("keeps the single lit pixel for a screen without scene", () => {
    for (const ecran of ["allume", "eteint"] as const) {
      const dessin = dessiner(ecran, false);
      expect(dessin.querySelector("svg"), ecran).toBeNull();
    }
  });

  it("plays an animation class on the scenes that move, only when animated", () => {
    for (const [ecran, classe] of [
      ["code", "anim-defile"],
      ["tests", "anim-avance"],
      ["audit", "anim-balaie"],
      ["diff", "anim-lueur"],
      ["criteres", "anim-lueur"],
    ] as const) {
      expect(classes(dessiner(ecran, true)), ecran).toContain(classe);
      expect(classes(dessiner(ecran, false)).filter((c) => c.startsWith("anim-")), ecran).toEqual([]);
    }
  });

  it("never animates the still page, the tick or the cross", () => {
    for (const ecran of ["lecture", "ok", "ko"] as const) {
      expect(classes(dessiner(ecran, true)).filter((c) => c.startsWith("anim-")), ecran).toEqual([]);
    }
  });

  it("draws the diff in green and red and the verdicts in their own tone", () => {
    expect(classes(dessiner("diff", false))).toEqual(expect.arrayContaining(["fill-green-400", "fill-red-400"]));
    expect(classes(dessiner("ok", false))).toContain("fill-green-400");
    expect(classes(dessiner("ko", false))).toContain("fill-red-400");
  });

  it("keeps the old glow on the plain pixel when animated", () => {
    expect(classes(dessiner("allume", true))).toContain("anim-lueur");
    expect(classes(dessiner("allume", false))).not.toContain("anim-lueur");
  });
});
