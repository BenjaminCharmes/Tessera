import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { TENUES, physique } from "../../lib/bureau/physique";
import type { Physique } from "../../lib/bureau/physique";
import type { PosteId } from "../../lib/bureau/postesDuRun";
import Personnage from "./Personnage";

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
    for (const coiffure of ["court", "long", "chignon", "chauve"] as const) {
      const look: Physique = { peau: 3, cheveux: 2, coiffure, jupe: false };
      for (const pose of ["assis", "debout"] as const) {
        const tete = rendu("testeur", pose, look).querySelector('rect[data-partie="tete"]');
        expect(tete?.getAttribute("width"), `${coiffure} ${pose}`).toBe("6");
      }
    }
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
