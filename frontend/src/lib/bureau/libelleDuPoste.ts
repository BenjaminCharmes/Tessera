import type { EtatPoste, RoleAffiche } from "./postesDuRun";
import { LIBELLE_SANTE } from "../santeAgent";
import type { SanteAgent } from "../santeAgent";

const NOMS: Record<RoleAffiche, string> = {
  codeur: "Codeur",
  architect: "Architecte",
  testeur: "Testeur",
  securite: "Sécurité",
  reviewer: "Reviewer",
  validateur: "Validateur",
  resolveur: "Résolveur",
  "doc-technique": "Rédacteur technique",
  "doc-fonctionnelle": "Rédacteur fonctionnel",
};

/** Le nom du poste, tel qu'on le lit sous le bureau et dans son `aria-label`. */
export function nomDuPoste(poste: RoleAffiche): string {
  return NOMS[poste];
}

function motDeLEtat(etat: EtatPoste, sante: SanteAgent, auRepos: boolean): string {
  if (etat === "occupe") return LIBELLE_SANTE[sante];
  if (etat === "fait") return "a fini";
  return auRepos ? "libre" : "attend son tour";
}

/**
 * L'état d'un poste en mots : « Codeur, travaille », « Testeur, a fini »,
 * « Reviewer, attend son tour ». Un poste occupé prend le libellé de santé du
 * run ; les deux autres n'en ont pas. Dans une pièce sans run, personne
 * n'attend son tour : le poste est simplement « libre ».
 */
export function libelleDuPoste(
  poste: RoleAffiche,
  etat: EtatPoste,
  sante: SanteAgent,
  auRepos = false,
): string {
  return `${NOMS[poste]}, ${motDeLEtat(etat, sante, auRepos)}`;
}
