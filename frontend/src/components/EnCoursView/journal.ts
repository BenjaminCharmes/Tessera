/** Le niveau d'une ligne de sortie, lu sur son texte : les services n'écrivent pas de niveau structuré. */
export type NiveauDeLigne = "erreur" | "avertissement" | "info";

const ERREUR = /\b(error|erreur|exception|traceback|fatal)\b/i;
const AVERTISSEMENT = /\b(warn|warning|avertissement|deprecated)\b/i;

// « 0 error », « no errors » : un compte nul ou une absence n'est pas un échec.
const ABSENCE_D_ERREUR = /\b(0|no|zero|aucune?|sans)\s+(error|erreur|exception|fatal)s?\b/gi;

export function niveauDeLigne(ligne: string): NiveauDeLigne {
  if (ERREUR.test(ligne.replace(ABSENCE_D_ERREUR, ""))) return "erreur";
  if (AVERTISSEMENT.test(ligne)) return "avertissement";
  return "info";
}

/** ADR-026 : rouge pour l'échec, ambre pour l'avertissement, zinc sinon. */
export const TON_DE_LIGNE: Record<NiveauDeLigne, string> = {
  erreur: "text-red-300",
  avertissement: "text-amber-300",
  info: "text-zinc-300",
};

/**
 * L'identifiant du journal d'un service, partagé par son écran (`aria-controls`) et
 * son volet (`id`). Le nom d'un service peut porter une espace, qui couperait la
 * référence en deux : on l'encode, sans confondre « mon api » et « mon-api ».
 */
export function idDuJournal(service: { project_id: string; nom: string }): string {
  return `journal-${service.project_id}-${encodeURIComponent(service.nom)}`;
}
