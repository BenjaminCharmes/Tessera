import type { StreamState } from "../../hooks/streamState";
import { physique } from "./physique";
import type { Physique, Tenue } from "./physique";
import { POSTES, postesDuRun } from "./postesDuRun";
import type { PosteId } from "./postesDuRun";
import type { ProjetPourLaColonne } from "./aToi";

/** Combien de temps un agent reste aux RH après un repli de provider. */
export const DELAI_RH_MS = 20_000;

/** Le directeur et la recruteuse sont des figures de salle : ils n'ont pas de rôle de pipeline, seulement une tenue. */
export const TENUE_DU_DIRECTEUR: Tenue = { haut: "securite", capuche: false, cravate: true };
export const TENUE_DES_RH: Tenue = { haut: "validateur", capuche: false, cravate: false };
export const PHYSIQUE_DU_DIRECTEUR: Physique = physique("directeur", "reviewer");
export const PHYSIQUE_DES_RH: Physique = physique("rh", "validateur");

/** Un agent qui a quitté son poste pour une salle commune. */
export interface AgentEnSalle {
  projet: string;
  poste: PosteId;
}

/** Un agent aux RH : ce qui a été tenté, ce qui a répondu à la place. */
export interface AgentAuxRh extends AgentEnSalle {
  tente: string;
  utilise: string;
  modele: string;
}

/** Où se tiennent, pour un run, ses agents qui ont quitté leur poste. */
export interface LieuxDuRun {
  directeur: PosteId | null;
  rh: Omit<AgentAuxRh, "projet"> | null;
}

/**
 * Le poste d'un rôle, ou null si le rôle n'en a pas. L'architecte tient le poste
 * du codeur (ticket `design`). Un rôle sans poste — le résolveur, la
 * documentation — n'a rien à dessiner dans une pièce : un repli à son nom
 * n'amène donc personne aux RH.
 */
export function posteDuRole(role: string | null): PosteId | null {
  if (role === "architect") return "codeur";
  return POSTES.find((p) => p === role) ?? null;
}

/**
 * L'agent devant le directeur : celui du rôle en cours, tant que sa question
 * attend une réponse (ADR-025). À défaut de rôle lisible, le premier poste occupé.
 */
function agentAuDirecteur(etat: StreamState): PosteId | null {
  if (etat.pendingQuestion === null) return null;
  const courant = posteDuRole(etat.currentAgent);
  if (courant !== null) return courant;
  return postesDuRun(etat).find((p) => p.etat === "occupe")?.poste ?? null;
}

/** L'agent aux RH : celui du dernier repli, pendant `DELAI_RH_MS` seulement. */
function agentAuxRh(etat: StreamState, maintenant: number): LieuxDuRun["rh"] {
  const repli = etat.repli;
  if (repli === null || maintenant - repli.a >= DELAI_RH_MS) return null;
  const poste = posteDuRole(repli.role);
  if (poste === null) return null;
  return { poste, tente: repli.tente, utilise: repli.utilise, modele: repli.modele };
}

/** Un agent ne peut être qu'à un endroit : le directeur, qui attend une réponse, passe avant les RH. */
export function lieuxDuRun(etat: StreamState, maintenant: number): LieuxDuRun {
  const directeur = agentAuDirecteur(etat);
  const rh = agentAuxRh(etat, maintenant);
  return { directeur, rh: rh !== null && rh.poste === directeur ? null : rh };
}

/** Les postes dont l'agent n'est pas à sa place : la pièce ne les dessine pas deux fois. */
export function postesAbsents(etat: StreamState, maintenant: number): PosteId[] {
  const { directeur, rh } = lieuxDuRun(etat, maintenant);
  return [directeur, rh?.poste ?? null].filter((p): p is PosteId => p !== null);
}

/** Les agents devant le directeur, tous projets confondus. */
export function agentsAuDirecteur(projets: readonly ProjetPourLaColonne[], maintenant: number): AgentEnSalle[] {
  return projets.flatMap(({ nom, etat }) => {
    const { directeur } = lieuxDuRun(etat, maintenant);
    return directeur === null ? [] : [{ projet: nom, poste: directeur }];
  });
}

/** Les agents aux RH, tous projets confondus. */
export function agentsAuxRh(projets: readonly ProjetPourLaColonne[], maintenant: number): AgentAuxRh[] {
  return projets.flatMap(({ nom, etat }) => {
    const { rh } = lieuxDuRun(etat, maintenant);
    return rh === null ? [] : [{ projet: nom, ...rh }];
  });
}
