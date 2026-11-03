/**
 * Le rejeu de l'historique d'un run vivant dans le store — ticket-325.
 *
 * Extrait de `useSupervision`, dont le plafond de longueur ne laissait plus de
 * place au rattachement des replis de provider (ticket-597).
 */
import { api } from "../lib/api";
import type { OrchestratorEvent, RunEvent } from "../types/api";
import { INITIAL, applyEvent } from "./streamState";
import type { StreamState } from "./streamState";
import { runStore } from "./runStore";

/**
 * Charge les événements persistés du run et les rejoue dans le store, puis y
 * ajoute ceux du tampon que l'historique ne contient pas. `tampon` se relit après
 * l'attente : des événements en direct ont pu arriver pendant le chargement.
 * Historique indisponible : le tampon se vide sur l'état courant.
 */
export async function rejouerHistorique(
  runId: string,
  dbRunId: string,
  tampon: () => readonly OrchestratorEvent[],
): Promise<void> {
  try {
    const evts: RunEvent[] = await api.runs.events(dbRunId);
    const dernierTs = evts.length > 0 ? evts[evts.length - 1].timestamp : null;
    let etat: StreamState = INITIAL;
    for (const ev of evts) {
      etat = applyEvent(etat, { ...ev, ticket_id: "", run_id: runId } as OrchestratorEvent);
    }
    for (const ev of tampon()) {
      if (!dernierTs || ev.timestamp > dernierTs) etat = applyEvent(etat, ev);
    }
    runStore.set(runId, etat);
  } catch {
    let etat = runStore.getSnapshot()[runId] ?? INITIAL;
    for (const ev of tampon()) etat = applyEvent(etat, ev);
    runStore.set(runId, etat);
  }
}
