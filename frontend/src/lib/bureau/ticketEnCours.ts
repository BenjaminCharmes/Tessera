import type { StreamState } from "../../hooks/streamState";
import type { RunActif } from "../../types/api";

/** Le ticket que la pièce traite : son identifiant et, si on le connaît, son titre. */
export interface TicketEnCours {
  id: string;
  titre: string | null;
}

/**
 * Le ticket en cours d'une pièce — ticket-656.
 *
 * La pile de dossiers ne montre que les tickets suivants : un run d'un seul ticket
 * n'affichait le sien nulle part. L'identifiant vient de l'état du run (instantané,
 * `queue_progress` ou événements du ticket), à défaut du run ; le titre, du run, que le
 * backend tient à jour à chaque `ticket_status_changed`, file comprise. Pas de lecture
 * des tickets par pièce : elle ajouterait un minuteur à chacune.
 */
export function ticketEnCours(
  etat: StreamState,
  run: RunActif | undefined,
): TicketEnCours | null {
  const id =
    etat.ticketId ??
    etat.ticketEvents.find((ev) => ev.ticket_id)?.ticket_id ??
    run?.ticket_id ??
    null;
  if (!id) return null;
  const titre = run?.ticket_id === id ? (run.ticket_titre ?? null) : null;
  return { id, titre };
}
