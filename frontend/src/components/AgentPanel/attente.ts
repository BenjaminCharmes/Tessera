/**
 * Ce qu'il reste avant qu'un agent reprenne seul — ticket-186.
 *
 * ADR-025 fait repartir un agent sur une hypothèse énoncée passé
 * `dialogue_timeout_s`. L'attente est donc bornée, mais rien ne le disait à
 * l'écran : cinq minutes de silence se lisent comme une panne.
 */

/**
 * Les millisecondes restantes, ou `null` si l'échéance est inconnue ou
 * illisible. `0` quand elle est passée — l'agent est en train de reprendre.
 */
export function resteAvant(
  expireA: string | null,
  maintenant: number,
): number | null {
  if (!expireA) return null;
  const echeance = Date.parse(expireA);
  if (Number.isNaN(echeance)) return null;
  return Math.max(0, echeance - maintenant);
}

/**
 * La phrase affichée sous une question en attente.
 *
 * Sans échéance lisible, on ne promet rien : annoncer un délai faux est pire
 * que n'en annoncer aucun.
 */
export function libelleDeLAttente(reste: number | null): string | null {
  if (reste === null) return null;
  if (reste === 0) return "L'agent reprend sur sa propre hypothèse.";
  const secondes = Math.ceil(reste / 1000);
  if (secondes < 60) return `Sans réponse, l'agent reprend dans ${secondes}s.`;
  const minutes = Math.floor(secondes / 60);
  const reliquat = secondes % 60;
  return `Sans réponse, l'agent reprend dans ${minutes}m ${reliquat}s.`;
}
