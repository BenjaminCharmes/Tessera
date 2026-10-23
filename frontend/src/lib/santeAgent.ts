/**
 * Santé visible d'un agent en cours (ticket-549).
 *
 * L'état se déduit du temps écoulé depuis le dernier événement du run : aucun
 * événement backend de plus. Il ne coupe rien — `agent_silence_max_s` reste le
 * seul arrêt.
 */
export type SanteAgent = "actif" | "attente" | "blocage_suspecte" | "question";

/** Au-delà, l'agent est « silencieux » : il réfléchit, ou attend un outil. */
export const SEUIL_ATTENTE_MS = 30_000;
/** Au-delà, un blocage est suspecté. */
export const SEUIL_BLOCAGE_MS = 180_000;

/**
 * Une question en attente prime (ADR-025) : l'agent attend l'humain, il n'est pas figé.
 * Un horodatage absent ou illisible rend `actif` : sans événement, on ne conclut rien.
 */
export function santeAgent(
  dernierEvenementA: string | null | undefined,
  maintenant: number,
  questionEnAttente: string | null | undefined,
): SanteAgent {
  if (questionEnAttente) return "question";
  if (!dernierEvenementA) return "actif";
  const ecart = maintenant - Date.parse(dernierEvenementA);
  if (Number.isNaN(ecart)) return "actif";
  if (ecart > SEUIL_BLOCAGE_MS) return "blocage_suspecte";
  if (ecart > SEUIL_ATTENTE_MS) return "attente";
  return "actif";
}
