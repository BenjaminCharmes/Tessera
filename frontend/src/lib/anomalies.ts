import type { RegleAnomalie } from "../types/runs";

/** Ce que dit chaque règle du détecteur d'anomalies (ADR-078) : un mot pour la cloche et le fil. */
export const LIBELLES_REGLE: Record<RegleAnomalie, string> = {
  outil_repete: "outil répété",
  etape_longue: "étape trop longue",
  silence: "silence prolongé",
  cout_anormal: "coût anormal",
  tours_de_revue: "dernier tour de revue",
  blocages_identiques: "blocages identiques",
  documentation_refusee_en_serie: "documentation refusée en série",
};

/** Le libellé d'une règle ; une règle que ce client ne connaît pas se rend avec son identifiant brut. */
export function libelleDeRegle(regle: string): string {
  return (LIBELLES_REGLE as Record<string, string | undefined>)[regle] ?? regle;
}
