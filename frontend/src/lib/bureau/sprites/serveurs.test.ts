import { describe, expect, it } from "vitest";
import type { Sprite } from "./grille";
import { ETAT_DU_VOYANT, baieHaute, boucheVmc, climatiseur, extincteur, petiteBaie, porteCoupeFeu } from "./serveurs";

function jetons(s: Sprite): string[] {
  return s.calques.flatMap(({ g }) => g.p.flatMap((c) => (c ? [c.replace("~r", "")] : [])));
}
const etats = (s: Sprite) => new Set(jetons(s).filter((t) => t.startsWith("etat-")).map((t) => t.split(".")[0]));

describe("server room", () => {
  it("lights the rack lamp in its service state, and blinks a diode per server while it runs", () => {
    expect(etats(baieHaute("echoue"))).toEqual(new Set(["etat-blocage"]));
    expect(baieHaute("en-cours").calques.filter((c) => c.classe === "anim-clignote")).toHaveLength(7);
    expect(baieHaute("arrete").calques.some((c) => c.classe)).toBe(false);
    expect(ETAT_DU_VOYANT["jamais-lance"]).toBe("attente");
  });

  it("stacks one 2U server per service in the small rack", () => {
    expect(petiteBaie(["en-cours", "echoue", "arrete"]).h).toBe(28);
    expect(etats(petiteBaie(["en-cours", "echoue"]))).toEqual(new Set(["etat-actif", "etat-blocage"]));
  });

  it("spins the vent fan only with a duration, behind a half-transparent grille", () => {
    const tourne = boucheVmc("0.6s");
    expect(tourne.calques.find((c) => c.classe === "anim-helice")?.style?.animationDuration).toBe("0.6s");
    expect(boucheVmc(null).calques.some((c) => c.classe)).toBe(false);
    expect(tourne.calques.at(-1)?.style?.opacity).toBe("0.6");
  });

  it("keeps the air conditioner, the extinguisher and the fire door as furniture", () => {
    for (const s of [climatiseur(), extincteur(), porteCoupeFeu()]) {
      expect(etats(s).size).toBe(0);
      expect(s.calques.every((c) => c.classe === "")).toBe(true);
    }
  });
});
