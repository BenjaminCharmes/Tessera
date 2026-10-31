import { useMemo } from "react";
import { statutsDuRun } from "../lib/statutDuRun";
import type { StreamState } from "./streamState";
import { usePolling } from "./usePolling";
import { useResource } from "./useResource";

const CADENCE_MS = 30_000;
const AUCUN: readonly string[] = [];

/**
 * Les tickets qu'il reste à traiter dans la file d'un run — ticket-563.
 *
 * Relus dans `GET /runs/{id}` à chaque `queue_progress`, et toutes les 30 s
 * tant que le run vit et que la fenêtre est visible. Sans `runId`, rien n'est
 * demandé et aucun minuteur ne bat.
 *
 * Le signal est le `queue_progress` lui-même : `ticketEvents` repart de zéro à
 * chaque annonce, donc il en est le premier élément. `queue` ne convient pas,
 * son index ne bouge pas toujours entre deux annonces.
 */
export function useRestants(
  projet: string,
  runId: string | null,
  etat: StreamState,
): readonly string[] {
  const premier = etat.ticketEvents[0];
  const signal = premier?.type === "queue_progress" ? premier : null;

  const fetcher = useMemo(
    () => (runId ? () => statutsDuRun.lire(runId).then((statut) => statut.restants) : null),
    // `signal` ne sert pas dans le fetcher : changer l'identité de celui-ci est
    // le moyen de relire (voir `useResource`), exactement comme `useServices`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [runId, signal],
  );
  const { data, refresh } = useResource<readonly string[]>(
    fetcher,
    AUCUN,
    runId ? { projet, ressource: `restants:${runId}` } : undefined,
  );

  usePolling(refresh, { cadenceMs: runId && !etat.runClosed ? CADENCE_MS : null });

  return runId ? data : AUCUN;
}
