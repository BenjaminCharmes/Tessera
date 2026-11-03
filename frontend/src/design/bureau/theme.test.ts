import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { TENUES, type Physique } from "../../lib/bureau/physique";
import { cheminDeCables, dalles, murEnduit, plinthe, solParquet } from "../../lib/bureau/sprites/ambiance";
import { bureauEnBois, canape, chaise, classeur, frigo, tableDeReunion } from "../../lib/bureau/sprites/communs";
import { debout, marche } from "../../lib/bureau/sprites/debout";
import { scene } from "../../lib/bureau/sprites/ecrans";
import type { Sprite } from "../../lib/bureau/sprites/grille";
import { bibliotheque, etagere, machineACafe, meubleBas, plante } from "../../lib/bureau/sprites/mobilier";
import { fenetre, horloge, interrupteur, plafonnier, porte } from "../../lib/bureau/sprites/mur";
import { boite, confetti, corbeille, dossier, gyrophare, imprimante, vapeur } from "../../lib/bureau/sprites/objets";
import { poste } from "../../lib/bureau/sprites/poste";
import { baieHaute, boucheVmc, climatiseur, extincteur, petiteBaie, porteCoupeFeu } from "../../lib/bureau/sprites/serveurs";
import { cadre, cadreDore, tableauBlanc } from "../../lib/bureau/sprites/tableau";

/**
 * Le thème des sprites (ticket-727) : chaque jeton que le moteur pose doit avoir sa
 * variable dans `sprites-theme.css`, le jour comme la nuit — sinon le pixel ne se
 * peint pas, sans qu'aucun test de rendu ne le voie. Et un état garde sa teinte à
 * toute heure (ADR-026).
 */
const THEME = readFileSync(join(__dirname, "sprites-theme.css"), "utf-8");
const [JOUR = "", NUIT = ""] = THEME.split('[data-moment="nuit"]');

const PH: Physique = { peau: 1, cheveux: 7, coiffure: "carre", jupe: true };

const TOUS: Sprite[] = [
  solParquet(), murEnduit(), murEnduit("salle-mur"), plinthe(), dalles(), cheminDeCables(),
  canape(), frigo(), classeur(), tableDeReunion(), chaise(), bureauEnBois({ tenue: TENUES.reviewer, physique: PH }),
  ...(["tasse", "vides", "levees", "feuille"] as const).map((mains) => debout({ physique: PH, tenue: TENUES.codeur, expression: "fait", mains })),
  marche({ physique: { ...PH, jupe: false }, tenue: TENUES.reviewer, expression: "neutre", mains: "tasse" }),
  ...(["code", "lecture", "tests", "audit", "diff", "criteres", "ok", "ko"] as const).flatMap((e) => scene(e, "question", true) ?? []),
  bibliotheque(), etagere(), machineACafe(), meubleBas(), plante("pot"), plante("cactus"), plante("ficus"),
  fenetre({ jour: true, soleil: true, nuages: 2 }), fenetre({ jour: false, soleil: true, nuages: 0 }),
  horloge(10, 10), interrupteur(true), plafonnier(true), plafonnier(false), porte(),
  boite("ouverte"), boite("ci"), boite("mergee"), boite("refusee"), corbeille(3), dossier(), gyrophare(), imprimante(), vapeur(),
  ...[0, 1, 2, 3, 4].map(confetti),
  ...Object.values(TENUES).map((tenue) =>
    poste({ physique: PH, tenue, vide: false, expression: "blocage", tape: true, etatEcran: "attente", scene: false }),
  ),
  baieHaute("en-cours"), baieHaute("echoue"), petiteBaie(["arrete", "jamais-lance"]), boucheVmc("1s"), climatiseur(), extincteur(), porteCoupeFeu(),
  cadre(0), cadre(1), cadre(2), cadre(3), cadreDore(PH), tableauBlanc(["attente", "passe", "echoue"]),
];

function variables(): Set<string> {
  const jetons = TOUS.flatMap((s) => s.calques.flatMap(({ g }) => g.p.flatMap((c) => (c ? [(c.split("^")[0] ?? c).replace("~r", "")] : []))));
  return new Set(jetons.map((t) => `--sprite-${t.replace(".", "-")}`));
}

function valeur(bloc: string, nom: string): string | undefined {
  return bloc.match(new RegExp(`${nom}:\\s*([^;]+);`))?.[1];
}

describe("sprite theme", () => {
  it("defines every token the engine paints, by day and by night", () => {
    const manquantes = [...variables()].filter((v) => !valeur(JOUR, v) || !valeur(NUIT, v));
    expect(manquantes).toEqual([]);
  });

  it("keeps each state tone the same at night (ADR-026)", () => {
    const etats = [...JOUR.matchAll(/(--sprite-etat-[a-z]+-(?:hi|b|s|d)):/g)].map((m) => m[1] ?? "");
    expect(etats.length).toBeGreaterThan(0);
    for (const v of etats) expect(valeur(NUIT, v), v).toBe(valeur(JOUR, v));
  });

  it("is imported by index.css, under a static theme so var() finds it", () => {
    const css = readFileSync(join(__dirname, "..", "..", "index.css"), "utf-8");
    expect(css).toContain("sprites-theme.css");
    expect(JOUR).toContain("@theme static");
  });
});
