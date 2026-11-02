/**
 * Famille « run » du réducteur de `streamState.ts` (ticket-695) : ce qui
 * concerne le ticket ou le run entier — branche, titre, fin du pipeline,
 * livraison, merge, clôture, erreur, quota. Chaque fonction de famille rend le
 * morceau d'état à fusionner, ou null quand l'événement n'en est pas.
 */
import type { OrchestratorEvent, PipelineResult, QuotaState, TicketStatus } from "../types/api";
import { removeEtapeEnCours } from "./streamEtapes";
import type { StreamState } from "./streamState";

function appliquerFinDePipeline(s: StreamState, ev: OrchestratorEvent): Partial<StreamState> {
  const brut = ev.data["branch"];
  const branch = typeof brut === "string" ? brut : s.branch;
  // Le ticket_id est au premier niveau de l'événement (ev.ticket_id) ;
  // ev.data["ticket_id"] est un doublon de confort, pas toujours présent.
  const dansData = ev.data["ticket_id"];
  const rounds = ev.data["rounds"];
  const resultat: PipelineResult = {
    ticket_id: ev.ticket_id || (typeof dansData === "string" ? dansData : "") || s.ticketId || "",
    final_status: (ev.data["final_status"] as TicketStatus) ?? "done",
    rounds: typeof rounds === "number" ? rounds : 0,
    approved: ev.data["approved"] === true,
    branch,
  };
  return {
    status: "done",
    lastResult: resultat,
    etape: null,
    etapesEnCours: [],
    pendingQuestion: null,
    questionExpireA: null,
    branch,
  };
}

function appliquerLivraison(s: StreamState, ev: OrchestratorEvent): Partial<StreamState> {
  const pr = ev.data["pr_number"];
  return {
    etapesEnCours: removeEtapeEnCours(s.etapesEnCours, "livraison"),
    livraisonPrNumber: typeof pr === "number" ? pr : s.livraisonPrNumber,
  };
}

function appliquerMergeCi(ev: OrchestratorEvent): Partial<StreamState> {
  const arret = ev.data["arret"];
  return { ciMerge: { merged: ev.data["merged"] === true, arret: typeof arret === "string" ? arret : null } };
}

/** Les événements du run et du ticket : branche, titre, pipeline, livraison, CI, clôture, erreur, quota. */
export function appliquerRun(
  s: StreamState,
  ev: OrchestratorEvent,
): Partial<StreamState> | null {
  const d = ev.data;
  switch (ev.type) {
    case "branch_created":
      return { branch: typeof d["branch"] === "string" ? d["branch"] : s.branch };
    case "ticket_status_changed":
      // Quand le backend change le ticket courant (file), il inclut le titre
      // dans les données pour les observateurs connectés (ticket-286).
      return { ticketTitre: typeof d["ticket_titre"] === "string" ? d["ticket_titre"] : s.ticketTitre };
    case "pipeline_done":
      return appliquerFinDePipeline(s, ev);
    case "livraison_done":
      return appliquerLivraison(s, ev);
    case "ci_merge_done":
      return appliquerMergeCi(ev);
    case "run_closed":
      // Le run est terminé : livraison et documentation sont finies. Le bouton
      // « Fermer » n'apparaît qu'ici (ticket-267) ; l'étape se remet à null pour
      // que livraison ou doc ne clignotent plus (ticket-279).
      return { runClosed: true, etape: null, etapesEnCours: [] };
    case "error":
      return { status: "error", errorMessage: typeof d["message"] === "string" ? d["message"] : "Pipeline error" };
    case "quota_updated":
      // Le quota d'abonnement est la ressource réellement finie : l'afficher
      // évite d'être coupé sans comprendre pourquoi (ticket-054).
      return { quota: d as unknown as QuotaState };
    default:
      return null;
  }
}
