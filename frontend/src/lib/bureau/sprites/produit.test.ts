import { describe, expect, it } from "vitest";
import type { Physique } from "../physique";
import type { Sprite } from "./grille";
import { agentAuPupitre, baieGpu, pupitreVide } from "./produit";

const PH: Physique = { peau: 3, cheveux: 5, coiffure: "carre", jupe: false };

function jetons(s: Sprite): Set<string> {
  return new Set(s.calques.flatMap(({ g }) => g.p.flatMap((c) => (c ? [c.replace("~r", "")] : []))));
}
const classes = (s: Sprite) => s.calques.flatMap((c) => c.classe.split(" ").filter(Boolean));

describe("agentAuPupitre", () => {
  it("dresses the product agent in its own plain top, with the Bureau head", () => {
    const t = jetons(agentAuPupitre(PH, "actif"));
    expect(t).toContain("haut-produit.b");
    expect(t).toContain("peau3.b");
    expect(t).toContain("cheveux5.b");
  });

  it("types and scrolls its screen at work, stays still with a waiting screen at rest", () => {
    const actif = agentAuPupitre(PH, "actif");
    expect(classes(actif)).toContain("anim-tape");
    expect(classes(actif)).toContain("anim-trame-4");
    const repos = agentAuPupitre(PH, "repos");
    expect(classes(repos)).toEqual([]);
    expect(jetons(repos)).toContain("etat-attente.hi");
  });
});

describe("pupitreVide", () => {
  it("keeps the console dark, with no one and no state", () => {
    const s = pupitreVide();
    expect([...jetons(s)].some((t) => t.startsWith("etat-") || t.startsWith("peau"))).toBe(false);
    expect(classes(s)).toEqual([]);
  });
});

describe("baieGpu", () => {
  it("lights its lamp blue when available, amber and blinking while it cools down", () => {
    const etats = (s: Sprite) => new Set([...jetons(s)].filter((t) => t.startsWith("etat-")).map((t) => t.split(".")[0]));
    expect(etats(baieGpu("disponible"))).toEqual(new Set(["etat-actif"]));
    expect(classes(baieGpu("disponible"))).toEqual([]);
    expect(etats(baieGpu("refroidissement"))).toEqual(new Set(["etat-question"]));
    expect(classes(baieGpu("refroidissement"))).toEqual(["anim-gyro"]);
  });
});
