/** Le niveau d'une ligne de sortie, lu sur son texte : les services n'écrivent pas de niveau structuré. */
export type NiveauDeLigne = "erreur" | "avertissement" | "info";

const ERREUR = /\b(error|erreur|exception|traceback|fatal)\b/i;
const AVERTISSEMENT = /\b(warn|warning|avertissement|deprecated)\b/i;

export function niveauDeLigne(ligne: string): NiveauDeLigne {
  if (ERREUR.test(ligne)) return "erreur";
  if (AVERTISSEMENT.test(ligne)) return "avertissement";
  return "info";
}

/** ADR-026 : rouge pour l'échec, ambre pour l'avertissement, zinc sinon. */
export const TON_DE_LIGNE: Record<NiveauDeLigne, string> = {
  erreur: "text-red-300",
  avertissement: "text-amber-300",
  info: "text-zinc-300",
};
