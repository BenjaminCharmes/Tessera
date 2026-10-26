/**
 * Santé visible d'un agent en cours (ticket-549).
 *
 * L'état se déduit du temps écoulé depuis le dernier événement du run : aucun
 * événement backend de plus. Il ne coupe rien — `agent_silence_max_s` reste le
 * seul arrêt.
 */
export type SanteAgent = "actif" | "attente" | "blocage_suspecte" | "question";

/** Le mot qui dit la santé : un seul libellé pour la pastille du run et le Bureau. */
export const LIBELLE_SANTE: Record<SanteAgent, string> = {
  actif: "travaille",
  attente: "silencieux",
  blocage_suspecte: "figé ?",
  question: "question",
};

/** Au-delà, l'agent est « silencieux » : il réfléchit, ou attend un outil. */
export const SEUIL_ATTENTE_MS = 30_000;
/** Au-delà, un blocage est suspecté. */
export const SEUIL_BLOCAGE_MS = 180_000;

/**
 * Les étapes qui n'émettent aucun événement pendant leur travail (ticket-587) :
 * `tests` entre `test_started` et `test_result`, puis celles que `*_started`
 * ouvre. Seuls le codeur, l'architecte et le reviewer émettent en continu.
 */
const ETAPES_SILENCIEUSES: readonly string[] = [
  "tests",
  "securite",
  "validation",
  "documentation",
  "livraison",
];

/** Vrai quand une étape silencieuse tourne : son silence n'est pas un signe de blocage. */
export function enEtapeSilencieuse(etat: { etapesEnCours: readonly string[] }): boolean {
  return etat.etapesEnCours.some((e) => ETAPES_SILENCIEUSES.includes(e));
}

/**
 * Une question en attente prime (ADR-025) : l'agent attend l'humain, il n'est pas figé.
 * Une attente extérieure (`external_wait`) ne se confond pas avec un blocage : le
 * silence est voulu, quelle que soit sa durée, donc `attente` et jamais « figé ? ».
 * Une étape silencieuse (`etapeSilencieuse`, ticket-587) ne se confond pas non plus
 * avec un blocage : testeur, audit, validateur, documentation et livraison n'émettent
 * rien pendant qu'ils travaillent, et ont leur propre coupure côté backend. Le
 * silence reste lu comme `attente` au-delà de 30 s, mais ne monte jamais à « figé ? ».
 * Un horodatage absent ou illisible rend `actif` : sans événement, on ne conclut rien.
 */
export function santeAgent(
  dernierEvenementA: string | null | undefined,
  maintenant: number,
  questionEnAttente: string | null | undefined,
  attenteExterieure = false,
  etapeSilencieuse = false,
): SanteAgent {
  if (questionEnAttente) return "question";
  if (attenteExterieure) return "attente";
  if (!dernierEvenementA) return "actif";
  const ecart = maintenant - Date.parse(dernierEvenementA);
  if (Number.isNaN(ecart)) return "actif";
  if (ecart > SEUIL_BLOCAGE_MS) return etapeSilencieuse ? "attente" : "blocage_suspecte";
  if (ecart > SEUIL_ATTENTE_MS) return "attente";
  return "actif";
}
