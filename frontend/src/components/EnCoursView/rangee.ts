import type { AgentDuService } from "./AgentsDeProduit";

/** Les postes vides d'une salle sans agent : du mobilier, éteint (ADR-058). */
export const POSTES_VIDES = 3;

/** Combien de postes de `poste` pixels, séparés de `ecart`, tiennent dans `largeur` ; au moins un. */
export function capaciteDeLaRangee(largeur: number, poste: number, ecart: number): number {
  if (!(largeur > 0) || !(poste > 0)) return 1;
  return Math.max(1, Math.floor((largeur + ecart) / (poste + ecart)));
}

export interface Rangee {
  /** Les agents dessinés, ceux au travail d'abord. */
  visibles: AgentDuService[];
  /** Ceux qui n'ont pas trouvé de poste : le badge « +N » les compte. */
  enPlus: number;
}

/**
 * Ce que la rangée dessine (ticket-730). Une seule ligne au sol : au-delà de la
 * capacité, un poste cède la place au badge « +N ». Les agents au travail passent
 * devant ceux au repos ; l'ordre du produit est gardé dans chaque groupe.
 */
export function rangee(agents: readonly AgentDuService[], capacite: number): Rangee {
  const tries = [...agents.filter((a) => a.agent.etat === "actif"), ...agents.filter((a) => a.agent.etat !== "actif")];
  if (tries.length <= capacite) return { visibles: tries, enPlus: 0 };
  const places = Math.max(1, capacite - 1);
  return { visibles: tries.slice(0, places), enPlus: tries.length - places };
}
