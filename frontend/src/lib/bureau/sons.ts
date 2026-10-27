import type { StreamState } from "../../hooks/streamState";
import type { AgentPlace } from "./activites";
import type { Son } from "./synthese";

/** Aucun son pendant les 2 premières secondes de la vue : le rejeu de l'historique ne fait pas de rafale. */
export const OUVERTURE_MUETTE_MS = 2_000;

/** Au plus un son par seconde et par pièce. */
export const INTERVALLE_ENTRE_SONS_MS = 1_000;

/** Ce que la pièce montre et qui peut s'entendre ; un changement d'un signal à l'autre fait le son. */
export interface SignauxSonores {
  /** La PR vient d'être mergée : la pièce fête. */
  fete: boolean;
  /** La CI est rouge : le gyrophare tourne. */
  alarme: boolean;
  /** Combien d'agents sont à la machine à café. */
  machine: number;
  /** Combien d'`agent_started` le ticket a vus. */
  demarrages: number;
}

/** Les signaux sonores d'une pièce, lus dans son état et dans la place de ses agents. */
export function signauxSonores(
  etat: StreamState,
  fete: boolean,
  alarme: boolean,
  agents: readonly AgentPlace[],
): SignauxSonores {
  return {
    fete,
    alarme,
    machine: agents.filter((a) => !a.parti && a.activite === "machine").length,
    demarrages: etat.ticketEvents.filter((ev) => ev.type === "agent_started").length,
  };
}

/**
 * Les sons que fait le passage de `avant` à `apres`, du plus important au moins
 * important : fanfare, alarme, glouglou, frappes. Seule une montée fait un son.
 */
export function sonsDeLaTransition(avant: SignauxSonores, apres: SignauxSonores): Son[] {
  const sons: Son[] = [];
  if (apres.fete && !avant.fete) sons.push("fanfare");
  if (apres.alarme && !avant.alarme) sons.push("alarme");
  if (apres.machine > avant.machine) sons.push("glouglou");
  if (apres.demarrages > avant.demarrages) sons.push("frappes");
  return sons;
}
