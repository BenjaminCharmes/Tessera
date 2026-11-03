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
import { agentAuPupitre, baieGpu, pupitreVide } from "../../lib/bureau/sprites/produit";
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
  ...(["code", "lecture", "tests", "audit", "diff", "criteres", "ok", "ko"] as const).flatMap((e) =>
    (["actif", "attente", "question", "blocage", "fait"] as const).flatMap((ton) =>
      [true, false].flatMap((anime) => scene(e, ton, anime) ?? []),
    ),
  ),
  agentAuPupitre(PH, "actif"), agentAuPupitre({ ...PH, coiffure: "chauve" }, "repos"), pupitreVide(),
  baieGpu("disponible"), baieGpu("refroidissement"),
  bibliotheque(), etagere(), machineACafe(), meubleBas(), plante("pot"), plante("cactus"), plante("ficus"),
  fenetre({ jour: true, soleil: true, nuages: 2 }), fenetre({ jour: false, soleil: true, nuages: 0 }),
  horloge(10, 10), interrupteur(true), plafonnier(true), plafonnier(false), porte(),
  boite("ouverte"), boite("ci"), boite("mergee"), boite("refusee"), corbeille(3), dossier(), gyrophare(), imprimante(), vapeur(),
  ...[0, 1, 2, 3, 4].map(confetti),
  ...Object.values(TENUES).map((tenue) =>
    poste({ physique: PH, tenue, vide: false, expression: "blocage", tape: true, etatEcran: "attente", scene: false }),
  ),
  ...(["actif", "attente", "question", "blocage", "fait"] as const).map((etatEcran) =>
    poste({ physique: PH, tenue: TENUES.codeur, vide: false, expression: "actif", tape: false, etatEcran, scene: false }),
  ),
  poste({ physique: PH, tenue: TENUES.testeur, vide: true, expression: "neutre", tape: false, etatEcran: "attente", scene: false }),
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

  it("takes every state tone from its Tailwind family (ADR-026)", () => {
    // Chaque état garde sa famille : bleu actif, zinc en attente, ambre en question, rouge bloqué, vert fait.
    const familles: Record<string, string[]> = {
      actif: ["#93c5fd", "#60a5fa", "#3b82f6", "#2563eb", "#1d4ed8"],
      attente: ["#a1a1aa", "#71717a", "#52525b", "#3f3f46", "#27272a"],
      question: ["#fcd34d", "#fbbf24", "#f59e0b", "#d97706", "#b45309"],
      blocage: ["#fca5a5", "#f87171", "#ef4444", "#dc2626", "#b91c1c"],
      fait: ["#86efac", "#4ade80", "#22c55e", "#16a34a", "#15803d"],
    };
    const hors = [...JOUR.matchAll(/--sprite-etat-([a-z]+)-([a-z]+):\s*([^;]+);/g)].filter(
      ([, etat = "", , valeur = ""]) => !familles[etat]?.includes(valeur.trim().toLowerCase()),
    );
    expect(hors.map((m) => m[0])).toEqual([]);
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
