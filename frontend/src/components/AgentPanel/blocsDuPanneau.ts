import type { AgentRole, OrchestratorEvent } from "../../types/api";

/**
 * L'ordre dans lequel le pipeline donne la parole. Si le reviewer parle, le
 * codeur a parlé avant lui : c'est ce qui permet à un observateur tardif de
 * savoir ce qu'il a manqué.
 *
 * Deux rôles seulement, et c'est vérifié : les étapes de test, de sécurité et
 * de validation n'attribuent aucun agent à leurs événements — la base n'en
 * contient jamais d'autre. Les y ajouter « au cas où » ferait déduire des
 * choses d'une valeur qui n'arrive pas.
 */
const ORDRE: readonly string[] = ["codeur", "reviewer"];

function rang(agent: string | null): number {
  return agent === null ? -1 : ORDRE.indexOf(agent);
}

export interface BlocsDuPanneau {
  coderStarted: boolean;
  coderDone: boolean;
  reviewerStarted: boolean;
}

/**
 * Quels blocs le panneau affiche — ticket-182.
 *
 * Ils se dérivaient des seuls événements. Un observateur arrivé après le début
 * — onglet rechargé, socket rouverte — n'en a aucun : ils sont passés avant
 * lui. Le panneau restait donc vide pendant qu'un run travaillait, alors que
 * l'état semé par l'instantané (ticket-163) savait quel agent parle.
 *
 * L'état décide, les événements enrichissent.
 */
export function blocsDuPanneau(
  events: OrchestratorEvent[],
  currentAgent: AgentRole | null,
): BlocsDuPanneau {
  const courant = rang(currentAgent);
  const vu = (agent: string, type: string) =>
    events.some((e) => e.type === type && e.agent === agent);

  return {
    coderStarted: vu("codeur", "agent_started") || courant >= 0,
    coderDone: vu("codeur", "agent_done") || courant > rang("codeur"),
    reviewerStarted:
      vu("reviewer", "agent_started") || courant >= rang("reviewer"),
  };
}
