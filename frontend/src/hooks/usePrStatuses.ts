import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { useFenetreVisible } from "./useFenetreVisible";
import type { PRStatus } from "../types/api";

const POLL_INTERVAL_MS = 30_000;

/**
 * Charge l'état de toutes les PR d'un projet en une seule requête et le rend
 * sous forme de table `ticket_id → PRStatus` (ticket-367).
 *
 * - Ne démarre que si `projectId` est fourni et la fenêtre visible.
 * - Renouvelle toutes les 30 s tant qu'au moins une PR est `open`.
 * - S'arrête définitivement quand toutes les PR sont réglées, même si la
 *   fenêtre revient visible.
 * - Suspend le polling quand la fenêtre est cachée ; reprend au retour.
 */
export function usePrStatuses(
  projectId: string | null,
): Record<string, PRStatus> {
  const [statuses, setStatuses] = useState<Record<string, PRStatus>>({});
  const fenetreVisible = useFenetreVisible();

  // Évite de redemander après que toutes les PR sont réglées.
  const allSettledRef = useRef(false);
  // Permet d'annuler une réponse en vol à la destruction de l'effet.
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Réinitialiser l'état settled quand le projet change.
  const prevProjectIdRef = useRef<string | null>(null);
  if (prevProjectIdRef.current !== projectId) {
    allSettledRef.current = false;
    prevProjectIdRef.current = projectId;
  }

  useEffect(() => {
    if (!projectId || !fenetreVisible || allSettledRef.current) return;

    let cancelled = false;

    const doFetch = async () => {
      if (allSettledRef.current) return;
      try {
        const entries = await api.github.getPrStatuses(projectId);
        if (cancelled) return;
        const table: Record<string, PRStatus> = {};
        for (const e of entries) {
          table[e.ticket_id] = {
            state: e.state,
            ci_status: e.ci_status,
            pr_url: e.pr_url,
            pr_number: e.pr_number,
          };
        }
        setStatuses(table);
        // Arrêter le polling si toutes les PR connues sont réglées.
        const hasOpen = entries.some((e) => e.state === "open");
        if (!hasOpen) {
          allSettledRef.current = true;
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
        }
      } catch {
        // Erreur passagère : on réessaiera au prochain tick.
      }
    };

    doFetch();
    intervalRef.current = setInterval(doFetch, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [projectId, fenetreVisible]);

  return statuses;
}
