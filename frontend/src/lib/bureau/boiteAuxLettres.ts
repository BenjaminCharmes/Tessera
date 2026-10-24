import type { StreamState } from "../../hooks/streamState";
import type { OrchestratorEvent } from "../../types/api";

/**
 * `aucune` : pas de PR ; `ouverte` : PR ouverte, que rien ne mergera seul
 * (conflit résolu, arrêt de livraison) ; `ci` : la CI tourne, `CIWatcher` merge
 * ensuite ; `mergee` ; `refusee` : le watcher n'a pas mergé.
 */
export type EtatBoite = "aucune" | "ouverte" | "ci" | "mergee" | "refusee";

export interface BoiteAuxLettres {
  etat: EtatBoite;
  /** Numéro de la PR, ou null quand il n'y en a pas. */
  pr: number | null;
}

function numero(ev: OrchestratorEvent | undefined): number | null {
  const n = ev?.data["pr_number"];
  return typeof n === "number" ? n : null;
}

function dernier(evenements: readonly OrchestratorEvent[], type: OrchestratorEvent["type"]): number {
  return evenements.map((ev) => ev.type).lastIndexOf(type);
}

/**
 * La phase 2 (CI puis merge) est confiée à `CIWatcher` quand la PR existe et
 * que la livraison ne s'est pas arrêtée — sauf une PR orpheline, surveillée
 * malgré son `arret` (`orchestrator.py`). Un conflit résolu n'est jamais surveillé.
 */
function surveilleeParLeWatcher(livraison: OrchestratorEvent): boolean {
  const arret = livraison.data["arret"];
  const sansArret = arret === null || arret === undefined || arret === "";
  return sansArret || livraison.data["pr_orpheline"] === true;
}

/**
 * L'état de la boîte aux lettres du run, lu dans `ticketEvents`.
 *
 * Un `ci_merge_done` ne vaut que s'il suit le dernier `livraison_done` : celui
 * d'avant parlerait d'une autre livraison.
 */
export function boiteAuxLettres(etat: StreamState): BoiteAuxLettres {
  const evenements = etat.ticketEvents;
  const iLivraison = dernier(evenements, "livraison_done");
  const iCi = dernier(evenements, "ci_merge_done");
  const livraison = iLivraison >= 0 ? evenements[iLivraison] : undefined;
  const ci = iCi > iLivraison ? evenements[iCi] : undefined;
  const pr = numero(livraison) ?? numero(ci);

  if (ci) return { etat: ci.data["merged"] === true ? "mergee" : "refusee", pr };
  if (!livraison || pr === null) return { etat: "aucune", pr: null };
  return { etat: surveilleeParLeWatcher(livraison) ? "ci" : "ouverte", pr };
}
