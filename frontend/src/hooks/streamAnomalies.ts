/**
 * L'entrée du fil que `run_anomaly` ajoute (ticket-840, ADR-078). Famille du
 * réducteur de `streamState.ts`, pure comme lui : rend le morceau d'état à
 * fusionner, ou null quand l'événement n'en est pas.
 */
import type { OrchestratorEvent } from "../types/api";
import type { EntreeAnomalie } from "./streamEntrees";
import type { StreamState } from "./streamState";

function texte(data: Record<string, unknown>, cle: string): string {
  const v = data[cle];
  return typeof v === "string" ? v : "";
}

export function appliquerAnomalie(s: StreamState, ev: OrchestratorEvent): Partial<StreamState> | null {
  if (ev.type !== "run_anomaly") return null;
  const cle = texte(ev.data, "cle");
  // Un même épisode relu (reconnexion, historique) ne s'affiche qu'une fois.
  if (cle !== "" && s.entries.some((e) => e.genre === "anomalie" && e.cle === cle)) return {};
  const entree: EntreeAnomalie = {
    genre: "anomalie",
    id: `anomalie-${s.entries.length}`,
    cle,
    regle: texte(ev.data, "regle"),
    message: texte(ev.data, "message"),
    isDone: true,
  };
  return { entries: [...s.entries, entree] };
}
