import { useMemo } from "react";
import { api } from "../../lib/api";
import { useResource } from "../../hooks/useResource";
import { decouperDiff, type FichierDiff } from "../DiffView/parse";
import type { Ticket, TicketDiff, TicketStatus } from "../../types/api";

/**
 * Le ticket dont on montre les fichiers touchés : celui qui est sélectionné,
 * sinon le dernier terminé (le plus récemment créé — le ticket ne porte pas de
 * date de fin).
 */
export function ticketDuDernierRun(
  selectionne: Ticket | null,
  byStatus: Record<TicketStatus, Ticket[]>,
): Ticket | null {
  if (selectionne) return selectionne;
  const termines = byStatus.done ?? [];
  return termines.reduce<Ticket | null>(
    (dernier, t) => (dernier === null || t.created > dernier.created ? t : dernier),
    null,
  );
}

interface Touches {
  fichiers: FichierDiff[];
  erreur: string | null;
}

/** Les fichiers du diff d'un ticket, avec lignes ajoutées et retirées. */
export function useFichiersTouches(
  projectId: string,
  ticket: Ticket | null,
): Touches {
  // L'identifiant, pas l'objet : la liste des tickets se relit et change de
  // référence sans que le ticket change.
  const ticketId = ticket?.id ?? null;
  const fetcher = useMemo(
    () => (ticketId ? () => api.tickets.diff(projectId, ticketId) : null),
    [projectId, ticketId],
  );
  const { data, error } = useResource<TicketDiff | null>(fetcher, null);
  const fichiers = useMemo(() => decouperDiff(data?.diff ?? ""), [data?.diff]);
  return { fichiers, erreur: error };
}
