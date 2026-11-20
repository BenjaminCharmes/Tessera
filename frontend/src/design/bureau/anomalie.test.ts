import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { marqueurAnomalie } from "../../lib/bureau/sprites/objets";

const THEME = readFileSync(join(__dirname, "sprites-theme.css"), "utf-8");
const [JOUR = "", NUIT = ""] = THEME.split('[data-moment="nuit"]');

const AMBRE = ["#fcd34d", "#fbbf24", "#f59e0b", "#d97706", "#b45309"];

function valeur(bloc: string, nom: string): string | undefined {
  return bloc.match(new RegExp(`${nom}:\\s*([^;]+);`))?.[1]?.trim().toLowerCase();
}

describe("etat-anomalie token (ADR-078, ADR-026)", () => {
  it("test_etat_anomalie_token_is_amber_and_identical_by_day_and_by_night", () => {
    for (const ton of ["hi", "b", "s", "d", "bl", "ol"]) {
      const nom = `--sprite-etat-anomalie-${ton}`;
      const jour = valeur(JOUR, nom);
      expect(jour, nom).toBeDefined();
      expect(AMBRE, nom).toContain(jour);
      expect(valeur(NUIT, nom), nom).toBe(jour);
    }
  });

  it("draws the marker in the anomaly tone only, still, without animation", () => {
    const s = marqueurAnomalie();
    const jetons = s.calques.flatMap(({ g }) => g.p.flatMap((c) => (c ? [c] : [])));

    expect(jetons.length).toBeGreaterThan(0);
    expect(jetons.every((t) => t.startsWith("etat-anomalie."))).toBe(true);
    expect(s.calques.map((c) => c.classe).filter(Boolean)).toEqual([]);
  });
});
