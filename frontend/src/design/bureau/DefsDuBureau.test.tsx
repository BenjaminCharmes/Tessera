import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { TENUES } from "../../lib/bureau/physique";
import { poste } from "../../lib/bureau/sprites/poste";
import DefsDuBureau from "./DefsDuBureau";
import SpriteSvg from "./SpriteSvg";

const dessin = poste({
  physique: { peau: 1, cheveux: 2, coiffure: "carre", jupe: false },
  tenue: TENUES.reviewer,
  vide: false,
  expression: "neutre",
  tape: false,
  etatEcran: "attente",
  scene: false,
});

describe("DefsDuBureau", () => {
  it("is empty when no sprite is mounted", () => {
    const { container } = render(<DefsDuBureau />);
    expect(container.querySelectorAll("symbol")).toHaveLength(0);
  });

  it("holds each layer once however many sprites use it, and drops it with the last", () => {
    const { container, rerender } = render(
      <>
        <DefsDuBureau />
        <SpriteSvg sprite={dessin} largeur={70} hauteur={63} />
        <SpriteSvg sprite={dessin} largeur={70} hauteur={63} />
      </>,
    );
    const symboles = container.querySelectorAll("symbol");
    const uses = container.querySelectorAll("use");
    expect(symboles.length).toBeGreaterThan(0);
    expect(uses.length).toBe(2 * symboles.length);
    for (const use of uses) expect(container.querySelector(use.getAttribute("href") ?? "")).not.toBeNull();

    rerender(<DefsDuBureau />);
    expect(container.querySelectorAll("symbol")).toHaveLength(0);
  });
});
