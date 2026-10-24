import { useEffect, useMemo } from "react";
import { api } from "../lib/api";
import type { StreamState } from "./streamState";
import { useFenetreVisible } from "./useFenetreVisible";
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
  const fenetreVisible = useFenetreVisible();

  const fetcher = useMemo(
    () => (runId ? () => api.runs.status(runId).then((statut) => statut.restants) : null),
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

  useEffect(() => {
    if (!runId || etat.runClosed || !fenetreVisible) return;
    const minuteur = setInterval(refresh, CADENCE_MS);
    return () => clearInterval(minuteur);
  }, [runId, etat.runClosed, fenetreVisible, refresh]);

  return runId ? data : AUCUN;
}
