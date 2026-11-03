import { describe, expect, it, vi } from "vitest";
import { TENUES, physique, type Physique } from "../physique";
import { cuire, sprite } from "./grille";
import { type OptionsPoste, poste } from "./poste";
import {
  abonner,
  empreinte,
  inscrire,
  instanceDuCalque,
  instancesDuSprite,
  liberer,
  symbolesInscrits,
} from "./symboles";

const AGENT: Physique = { peau: 2, cheveux: 1, coiffure: "court", jupe: false };

function posteDe(ph: Physique, o: Partial<OptionsPoste> = {}) {
  return poste({
    physique: ph,
    tenue: TENUES.codeur,
    vide: false,
    expression: "actif",
    tape: true,
    etatEcran: "actif",
    scene: false,
    ...o,
  });
}

const ids = (s: ReturnType<typeof posteDe>) => instancesDuSprite(s).map((i) => i.symbole.id);

describe("empreinte", () => {
  it("is stable and tells two contents apart", () => {
    expect(empreinte("abc")).toBe(empreinte("abc"));
    expect(empreinte("abc")).not.toBe(empreinte("abd"));
  });
});

describe("instanceDuCalque", () => {
  it("returns null for an empty layer", () => {
    const s = sprite(4, 4);
    expect(instanceDuCalque({ g: s.calque(), classe: "" }, 4, 4)).toBeNull();
  });

  it("keeps the animation class on the instance, not in the symbol", () => {
    const s = sprite(4, 4);
    const g = s.calque("anim-tape");
    g.rect(1, 1, 2, 2, "metal.b");
    const instance = instanceDuCalque({ g, classe: "anim-tape" }, 4, 4);
    expect(instance?.classe).toBe("anim-tape");
    expect(instance?.symbole.chemins[0]?.fill).toBe("var(--sprite-metal-b)");
  });

  it("binds the agent families on the use, never in the symbol", () => {
    const s = sprite(4, 4);
    const g = s.calque();
    g.rect(0, 0, 2, 2, "peau3.b");
    const instance = instanceDuCalque({ g, classe: "" }, 4, 4);
    expect(instance?.symbole.chemins[0]?.fill).toBe("var(--sp-peau-b)");
    expect(instance?.style["--sp-peau-b"]).toBe("var(--sprite-peau3-b)");
  });
});

describe("instancesDuSprite", () => {
  it("computes the instances once per sprite object", () => {
    const s = cuire(posteDe(AGENT));
    expect(instancesDuSprite(s)).toBe(instancesDuSprite(s));
  });

  it("shares the chair, desk and frame between any two seated agents of the same haircut", () => {
    const a = ids(posteDe(AGENT));
    const b = ids(posteDe({ ...AGENT, peau: 5, cheveux: 4 }, { expression: "attente", etatEcran: "attente", tape: false }));
    // Chaise, bureau, cadre : calques 0, 2 et 4.
    for (const k of [0, 2, 4]) expect(b[k]).toBe(a[k]);
  });

  it("shares a seated agent's drawing across skin, hair colour and role tones", () => {
    // Deux tenues sans capuche ni cravate : seules leurs couleurs diffèrent.
    const a = instancesDuSprite(posteDe(AGENT, { tenue: TENUES.testeur }));
    const b = instancesDuSprite(
      posteDe({ ...AGENT, peau: 4, cheveux: 3 }, { tenue: TENUES.architect, etatEcran: "question" }),
    );
    expect(b[1]?.symbole.id).toBe(a[1]?.symbole.id);
    expect(b[1]?.style["--sp-peau-b"]).toBe("var(--sprite-peau4-b)");
    expect(b[1]?.style["--sp-lueur"]).toBe("var(--sprite-etat-question-hi)");
  });

  it("does not share between two haircuts", () => {
    const court = ids(posteDe(AGENT));
    const long = ids(posteDe({ ...AGENT, coiffure: "long" }));
    expect(long[1]).not.toBe(court[1]);
  });

  it("gives a status layer its own state tokens, never a generic one", () => {
    const ecran = instancesDuSprite(posteDe(physique("p", "codeur"), { etatEcran: "blocage" })).at(-1);
    expect(ecran?.symbole.chemins.map((c) => c.fill)).toContain("var(--sprite-etat-blocage-hi)");
  });
});

describe("symbol registry", () => {
  const contenu = { id: "sp-test", w: 1, h: 1, chemins: [{ d: "M0 0h1v1h-1z", fill: "var(--sprite-metal-b)" }] };

  it("adds a symbol on its first use and removes it after its last", () => {
    const avertir = vi.fn();
    const desabonner = abonner(avertir);
    inscrire(contenu);
    inscrire(contenu);
    expect(symbolesInscrits()).toContainEqual(contenu);
    expect(avertir).toHaveBeenCalledTimes(1);
    liberer(contenu.id);
    expect(symbolesInscrits()).toContainEqual(contenu);
    liberer(contenu.id);
    expect(symbolesInscrits()).not.toContainEqual(contenu);
    expect(avertir).toHaveBeenCalledTimes(2);
    desabonner();
  });

  it("keeps the same snapshot while nothing changes", () => {
    expect(symbolesInscrits()).toBe(symbolesInscrits());
  });

  it("ignores a release of an unknown symbol", () => {
    expect(() => liberer("sp-inconnu")).not.toThrow();
  });
});
