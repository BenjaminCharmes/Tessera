import type { StreamState } from "../../hooks/streamState";
import type { OrchestratorEvent } from "../../types/api";
import type { PosteId } from "./postesDuRun";

/** Le tour de plan (`plan: true`) s'annonce par `data.phase: "plan"`, sous l'agent du codeur. */
export function estTourDePlan(ev: OrchestratorEvent): boolean {
  return (
    (ev.type === "agent_started" || ev.type === "agent_done") &&
    ev.data["phase"] === "plan"
  );
}

/**
 * Le poste dont l'agent prépare le plan : celui du codeur, de l'`agent_started` du
 * plan jusqu'à son `agent_done`. Le dernier événement d'agent tranche : un plan en
 * échec n'émet pas d'`agent_done`, mais le tour suivant (codeur) le referme ; un run
 * clos n'a plus personne au tableau.
 */
export function posteEnPlan(etat: StreamState): PosteId | null {
  if (etat.runClosed) return null;
  const dernier = etat.ticketEvents.findLast(
    (ev) => ev.type === "agent_started" || ev.type === "agent_done",
  );
  const enPlan = dernier?.type === "agent_started" && estTourDePlan(dernier);
  return enPlan ? "codeur" : null;
}
