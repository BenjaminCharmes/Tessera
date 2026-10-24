import type { EtatPoste, PosteId } from "./postesDuRun";
import { LIBELLE_SANTE } from "../santeAgent";
import type { SanteAgent } from "../santeAgent";

const NOMS: Record<PosteId, string> = {
  codeur: "Codeur",
  testeur: "Testeur",
  securite: "Sécurité",
  reviewer: "Reviewer",
  validateur: "Validateur",
};

/** Le nom du poste, tel qu'on le lit sous le bureau et dans son `aria-label`. */
export function nomDuPoste(poste: PosteId): string {
  return NOMS[poste];
}

/**
 * L'état d'un poste en mots : « Codeur, travaille », « Testeur, fait », « Reviewer, libre ».
 * Un poste occupé prend le libellé de santé du run ; les deux autres n'en ont pas.
 */
export function libelleDuPoste(poste: PosteId, etat: EtatPoste, sante: SanteAgent): string {
  const mot = etat === "occupe" ? LIBELLE_SANTE[sante] : etat === "fait" ? "fait" : "libre";
  return `${NOMS[poste]}, ${mot}`;
}
