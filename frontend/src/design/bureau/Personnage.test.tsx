import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { TENUES, physique } from "../../lib/bureau/physique";
import type { Physique } from "../../lib/bureau/physique";
import type { PosteId } from "../../lib/bureau/postesDuRun";
import Personnage from "./Personnage";
import Poste from "./Poste";
import Tete from "./Tete";

interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
  partie: string | undefined;
}

/** Les rects du rendu, en nombres, dans l'ordre de dessin. */
function rects(conteneur: HTMLElement): Rect[] {
  return [...conteneur.querySelectorAll("rect")].map((r) => ({
    x: Number(r.getAttribute("x")),
    y: Number(r.getAttribute("y")),
    w: Number(r.getAttribute("width")),
    h: Number(r.getAttribute("height")),
    partie: r.getAttribute("data-partie") ?? undefined,
  }));
}

function rendu(role: PosteId, pose: "assis" | "debout", look: Physique = physique("ide-core", role)) {
  return render(
    <svg>
      <Personnage tenue={TENUES[role]} physique={look} pose={pose} />
    </svg>,
  ).container;
}

describe("Personnage", () => {
  it("wears a tie on the reviewer and a hood on the coder", () => {
    expect(rendu("reviewer", "assis").querySelector('[data-detail="cravate"]')).not.toBeNull();
    expect(rendu("codeur", "assis").querySelector('[data-detail="capuche"]')).not.toBeNull();
    expect(rendu("reviewer", "debout").querySelector('[data-detail="cravate"]')).not.toBeNull();
    expect(rendu("codeur", "debout").querySelector('[data-detail="capuche"]')).not.toBeNull();
  });

  it("wears neither tie nor hood on the other roles", () => {
    for (const role of ["testeur", "securite", "validateur"] as const) {
      const c = rendu(role, "assis");
      expect(c.querySelector('[data-detail="cravate"]'), role).toBeNull();
      expect(c.querySelector('[data-detail="capuche"]'), role).toBeNull();
    }
  });

  it("draws a head of the same width, 6 units, seated and standing", () => {
    for (const pose of ["assis", "debout"] as const) {
      const tetes = [...rendu("codeur", pose).querySelectorAll('rect[data-partie="tete"]')];
      expect(tetes.map((t) => t.getAttribute("width")), pose).toEqual(["6"]);
    }
  });

  it("keeps the head width for every hairstyle", () => {
    for (const coiffure of ["court", "long", "carre", "chauve"] as const) {
      const look: Physique = { peau: 3, cheveux: 2, coiffure, jupe: false };
      for (const pose of ["assis", "debout"] as const) {
        const tete = rendu("testeur", pose, look).querySelector('rect[data-partie="tete"]');
        expect(tete?.getAttribute("width"), `${coiffure} ${pose}`).toBe("6");
      }
    }
  });

  it("draws a hair square on each temple, outside the eyes, for the short cut", () => {
    for (const pose of ["assis", "debout"] as const) {
      const look: Physique = { peau: 3, cheveux: 2, coiffure: "court", jupe: false };
      const c = rendu("testeur", pose, look);
      const tete = rects(c).find((r) => r.partie === "tete");
      const tempes = rects(c).filter((r) => r.partie === "tempe");

      expect(tete, pose).toBeDefined();
      const { x, y } = tete!;
      expect(tempes.map((t) => [t.x, t.y, t.w, t.h]), pose).toEqual([
        [x, y, 1, 1],
        [x + 5, y, 1, 1],
      ]);
    }
  });

  it("draws the bob as two locks beside the face, shorter than long hair, and nothing on top", () => {
    for (const pose of ["assis", "debout"] as const) {
      const look: Physique = { peau: 3, cheveux: 2, coiffure: "carre", jupe: false };
      const tous = rects(rendu("testeur", pose, look));
      const tete = tous.find((r) => r.partie === "tete")!;
      const meches = tous.filter((r) => r.w === 1 && r.h === 4 && r.y === tete.y - 1);

      expect(meches.map((m) => m.x), pose).toEqual([tete.x - 1, tete.x + 6]);
      expect(tous.some((r) => r.y < tete.y - 2), pose).toBe(false);
    }
  });

  it("lets the seated hair overflow the desk grid instead of being clipped", () => {
    const { container } = render(<Poste projet="ide-core" role="testeur" etat="libre" sante="actif" />);
    const svg = container.querySelector('[data-sprite="poste"]');

    expect(svg?.getAttribute("class")).toContain("overflow-visible");
  });

  it("leaves long and bald hair exactly as before", () => {
    const dessin = (coiffure: "long" | "chauve") =>
      rects(
        render(
          <svg>
            <Tete physique={{ peau: 3, cheveux: 2, coiffure, jupe: false }} x={10} y={10} />
          </svg>,
        ).container,
      ).map((r) => [r.x, r.y, r.w, r.h]);
    const visage = [10, 10, 6, 4];
    const yeux = [
      [11, 11, 1, 1],
      [14, 11, 1, 1],
    ];

    expect(dessin("long")).toEqual([[9, 9, 1, 7], [16, 9, 1, 7], [10, 8, 6, 2], visage, ...yeux]);
    expect(dessin("chauve")).toEqual([[10, 9, 1, 2], [15, 9, 1, 2], visage, [11, 9, 4, 1], ...yeux]);
  });

  it("colours the skin and the top from --sprite-* tokens", () => {
    const look: Physique = { peau: 4, cheveux: 1, coiffure: "court", jupe: false };
    const c = rendu("securite", "assis", look);

    expect(c.querySelector('rect[data-partie="tete"]')?.getAttribute("class")).toBe(
      "fill-(--sprite-peau-4)",
    );
    expect(c.innerHTML).toContain("fill-(--sprite-haut-securite)");
  });

  it("draws a skirt only when the look has one", () => {
    const sans: Physique = { peau: 2, cheveux: 1, coiffure: "long", jupe: false };
    const avec: Physique = { ...sans, jupe: true };

    const jupe = 'rect[width="8"][height="3"]';

    expect(rendu("testeur", "debout", avec).querySelectorAll(jupe)).toHaveLength(1);
    expect(rendu("testeur", "debout", sans).querySelectorAll(jupe)).toHaveLength(0);
  });

  it("types only when told to", () => {
    const role = "codeur";
    const calme = render(
      <svg>
        <Personnage tenue={TENUES[role]} physique={physique("ide-core", role)} />
      </svg>,
    ).container;
    const tape = render(
      <svg>
        <Personnage tenue={TENUES[role]} physique={physique("ide-core", role)} tape />
      </svg>,
    ).container;

    expect(calme.querySelector(".anim-tape")).toBeNull();
    expect(tape.querySelector(".anim-tape")).not.toBeNull();
  });
});
