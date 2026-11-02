/**
 * Famille « agents » du réducteur de `streamState.ts` (ticket-695) : jetons,
 * démarrage, fin et outils d'un agent. Chaque fonction de famille rend le
 * morceau d'état à fusionner, ou null quand l'événement n'en est pas.
 */
import type { OrchestratorEvent } from "../types/api";
import { addEtapeEnCours, removeEtapeEnCours } from "./streamEtapes";
import { dernierOutilDe, passageTermine } from "./streamEntrees";
import type { PassageAgent } from "./streamEntrees";
import type { StreamState } from "./streamState";

/** Étape que le rôle ouvre ou ferme : codeur = production, reviewer = revue. */
function etapeDuRole(agent: OrchestratorEvent["agent"]): string | null {
  if (agent === "codeur") return "production";
  if (agent === "reviewer") return "revue";
  return null;
}

/**
 * `agent_token` ne va ni dans `events` ni dans `ticketEvents` (ticket-353) : il
 * ne met à jour que `entries[…].tokens` et `currentTokens`, sans alourdir
 * l'historique ni déclencher de mise à jour de l'état racine par token.
 */
export function appliquerToken(s: StreamState, ev: OrchestratorEvent): StreamState {
  const brut = ev.data["token"];
  const token = ev.agent === "codeur" && typeof brut === "string" ? brut : "";
  if (!token) return s;
  const dernier = s.entries.reduceRight(
    (found, e, i) =>
      found === -1 && e.genre === "agent" && e.agent === "codeur" && !e.isDone ? i : found,
    -1,
  );
  const entries =
    dernier >= 0
      ? s.entries.map((e, i) =>
          i !== dernier || e.genre !== "agent" ? e : { ...e, tokens: e.tokens + token },
        )
      : s.entries;
  return { ...s, currentTokens: s.currentTokens + token, entries };
}

function appliquerDemarrage(s: StreamState, ev: OrchestratorEvent): Partial<StreamState> {
  const round = typeof ev.data["round"] === "number" ? ev.data["round"] : s.currentRound;
  const agent = ev.agent;
  const etapeRole = etapeDuRole(agent);
  // Un agent qui démarre referme les tests : sans `test_result` (commande
  // introuvable, délai dépassé), `tests` resterait « en cours » (ticket-587).
  const etapesEnCours = etapeRole
    ? addEtapeEnCours(removeEtapeEnCours(s.etapesEnCours, "tests"), etapeRole)
    : s.etapesEnCours;
  const entree: PassageAgent | null = agent
    ? { genre: "agent", id: `${agent}-${s.entries.length}`, agent, round, tokens: "", content: "", isDone: false }
    : null;
  const maxRounds = ev.data["max_rounds"];
  return {
    status: "running",
    currentAgent: agent,
    currentRound: round,
    etape: etapeRole ?? s.etape,
    etapesEnCours,
    maxRounds: typeof maxRounds === "number" ? maxRounds : s.maxRounds,
    currentTokens: "",
    outils: 0,
    entries: entree ? [...s.entries, entree] : s.entries,
  };
}

function appliquerFin(s: StreamState, ev: OrchestratorEvent): Partial<StreamState> {
  // Sans cela `currentAgent` restait figé sur le dernier agent démarré :
  // ses points de chargement continuaient de rebondir alors qu'il avait
  // rendu son verdict (ticket-073).
  const agent = ev.agent;
  const etape = etapeDuRole(agent);
  const coutAppel = ev.data["cost_usd"];
  // Le dernier passage non terminé de cet agent se referme.
  const dernier = s.entries.reduceRight(
    (found, e, i) =>
      found === -1 && e.genre === "agent" && e.agent === agent && !e.isDone ? i : found,
    -1,
  );
  return {
    currentAgent: s.currentAgent === agent ? null : s.currentAgent,
    etapesEnCours: etape ? removeEtapeEnCours(s.etapesEnCours, etape) : s.etapesEnCours,
    // Plus rien n'attend de réponse, et l'accusé n'a plus lieu d'être (ticket-358).
    pendingQuestion: null,
    questionExpireA: null,
    answerAck: null,
    coutUsd: s.coutUsd + (typeof coutAppel === "number" ? coutAppel : 0),
    appels: s.appels + 1,
    entries:
      dernier >= 0
        ? s.entries.map((e, i) =>
            i !== dernier || e.genre !== "agent" ? e : passageTermine(e, ev.data),
          )
        : s.entries,
  };
}

/** Les événements d'un agent, hors jetons : démarrage, fin, outil utilisé. */
export function appliquerAgent(
  s: StreamState,
  ev: OrchestratorEvent,
): Partial<StreamState> | null {
  switch (ev.type) {
    case "agent_started":
      return appliquerDemarrage(s, ev);
    case "agent_done":
      return appliquerFin(s, ev);
    case "agent_tool_use":
      return { outils: s.outils + 1, dernierOutil: dernierOutilDe(ev) ?? s.dernierOutil };
    default:
      return null;
  }
}
