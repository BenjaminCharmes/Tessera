/** Le plafond d'une revue de projet, en dollars (ticket-864, ADR-080). */
export const PLAFOND_REVUE_USD = 3;

/**
 * Le plus petit de 3 $ et du plafond de run ; un plafond de run à zéro veut dire
 * « sans plafond » : la revue garde alors ses 3 $. Même règle que
 * `plafond_de_revue` côté backend, qui reste la source : le run s'arrête à lui.
 */
export function plafondDeRevue(plafondDeRunUsd: number): number {
  if (plafondDeRunUsd <= 0) return PLAFOND_REVUE_USD;
  return Math.min(PLAFOND_REVUE_USD, plafondDeRunUsd);
}

/** Le ticket qu'un 409 « projet occupé » nomme entre parenthèses, s'il en nomme un. */
export function ticketEnCours(message: string): string | null {
  return /\((ticket-\d+)\)/.exec(message)?.[1] ?? null;
}
