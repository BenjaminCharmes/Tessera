/**
 * L'état d'un run, et comment un événement le fait avancer — ticket-129.
 *
 * Extrait de `useOrchestratorStream` quand le canal est devenu partagé : la
 * supervision suit **plusieurs** runs à la fois, donc la réduction doit
 * s'appliquer à un état quelconque, pas à celui d'un hook. Elle est pure, et
 * se teste sans monter de composant ni ouvrir de socket.
 */
import type {
  AgentRole,
  OrchestratorEvent,
  PipelineResult,
  QuotaState,
  RunActif,
  TicketStatus,
} from "../types/api";

export type StreamStatus = "idle" | "connecting" | "running" | "done" | "error";

export interface StreamState {
  status: StreamStatus;
  ticketId: string | null;
  events: OrchestratorEvent[];
  currentAgent: AgentRole | null;
  currentRound: number;
  currentTokens: string;
  lastResult: PipelineResult | null;
  errorMessage: string | null;
  /** Dernier état connu du quota d'abonnement, ou null tant que rien n'est remonté. */
  quota: QuotaState | null;
  /** Question posée par l'agent en cours, tant qu'on n'y a pas répondu (ticket-066). */
  pendingQuestion: string | null;
  /**
   * Quand l'agent reprendra seul (ADR-025), en ISO. Affiché en compte à
   * rebours : cinq minutes de silence se lisent comme une panne tant que
   * rien ne dit que l'attente est bornée (ticket-186).
   */
  questionExpireA: string | null;
  /** Avancement d'une file de tickets, ou null hors file (ticket-074). */
  queue: { index: number; total: number } | null;
  /**
   * Branche du run en cours, annoncée par `branch_created` puis confirmée par
   * `pipeline_done`. Sans elle, `TicketActivity` proposait de « lancer
   * d'abord le pipeline » après un run approuvé (ticket-123).
   */
  branch: string | null;
  /** Ce que le run a coûté jusqu'ici, et ce que l'agent en cours a consommé (ticket-197). */
  coutUsd: number;
  appels: number;
  outils: number;
  /** Nombre de tours du run, quand le backend le dit ; null sinon. */
  maxRounds: number | null;
}

export interface UseRunActifResult extends StreamState {
  connect: (ticketId: string) => void;
  /** Lance une sélection de tickets, dans l'ordre donné. */
  connectQueue: (ticketIds: string[]) => void;
  /**
   * Laisse l'IDE choisir lui-même les tickets, par priorité et dépendances.
   * `depuisGithub` tire d'abord les issues `agent-ready` du dépôt — jamais
   * par défaut : un appel réseau vers le dépôt d'un client ne part pas seul.
   */
  connectAutonome: (options: { depuisGithub: boolean }) => void;
  disconnect: () => void;
  clear: () => void;
  /** Répond à la question en cours et laisse le run reprendre. */
  answer: (text: string) => void;
  /** Dépose une consigne, lue par le prochain agent à parler. */
  interject: (text: string) => void;
  /** Demande l'arrêt du run ; il commitera ce qu'il a déjà produit. */
  stop: () => void;
}

export const INITIAL: StreamState = {
  status: "idle",
  ticketId: null,
  events: [],
  currentAgent: null,
  currentRound: 0,
  currentTokens: "",
  lastResult: null,
  errorMessage: null,
  quota: null,
  pendingQuestion: null,
  questionExpireA: null,
  queue: null,
  branch: null,
  maxRounds: null,
  coutUsd: 0,
  appels: 0,
  outils: 0,
};

/**
 * L'état d'un run tel que l'instantané permet de le reconstruire — ticket-163.
 *
 * `applyEvent` ne fabrique un état `running` que sur `agent_started`, émis une
 * seule fois au démarrage. Un observateur arrivé après — onglet ouvert en
 * retard, socket rouverte — restait donc `idle` pour toute la durée du run,
 * sans agents et, plus grave, sans la question en attente.
 */
export function etatDepuisRun(run: RunActif): StreamState {
  return {
    ...INITIAL,
    status: "running",
    ticketId: run.ticket_id,
    currentAgent: run.agent,
    currentRound: run.tour || INITIAL.currentRound,
    pendingQuestion: run.question ?? null,
    questionExpireA: run.question_expire_a ?? null,
    // Un F5 retrouve le cumul depuis l'instantané (ticket-197).
    coutUsd: run.cout_usd,
    appels: run.appels ?? 0,
    outils: run.outils ?? 0,
  };
}

export function applyEvent(s: StreamState, ev: OrchestratorEvent): StreamState {
  const events = [...s.events, ev];
  switch (ev.type) {
    case "agent_started":
      return {
        ...s,
        events,
        status: "running",
        currentAgent: ev.agent,
        currentRound:
          typeof ev.data["round"] === "number"
            ? ev.data["round"]
            : s.currentRound,
        maxRounds:
          typeof ev.data["max_rounds"] === "number"
            ? ev.data["max_rounds"]
            : s.maxRounds,
        currentTokens: "",
        outils: 0,
      };
    case "branch_created":
      return {
        ...s,
        events,
        branch:
          typeof ev.data["branch"] === "string" ? ev.data["branch"] : s.branch,
      };
    case "agent_done":
      // Sans cela `currentAgent` restait figé sur le dernier agent démarré :
      // ses points de chargement continuaient de rebondir alors qu'il avait
      // rendu son verdict (ticket-073).
      return {
        ...s,
        events,
        currentAgent: s.currentAgent === ev.agent ? null : s.currentAgent,
        coutUsd:
          s.coutUsd +
          (typeof ev.data["cost_usd"] === "number" ? ev.data["cost_usd"] : 0),
        appels: s.appels + 1,
      };
    case "agent_token":
    case "agent_tool_use":
      return {
        ...s,
        events,
        // L'agent a repris — sur réponse, ou seul passé le délai (ADR-025).
        // Garder la question ferait répondre à un agent qui n'écoute plus ;
        // le registre l'efface déjà, un client en direct ne le faisait pas
        // (ticket-186).
        pendingQuestion: null,
        questionExpireA: null,
        outils: ev.type === "agent_tool_use" ? s.outils + 1 : s.outils,
        currentTokens:
          ev.agent === "codeur"
            ? s.currentTokens +
              (typeof ev.data["token"] === "string" ? ev.data["token"] : "")
            : s.currentTokens,
      };
    case "pipeline_done": {
      const branch =
        typeof ev.data["branch"] === "string" ? ev.data["branch"] : s.branch;
      const result: PipelineResult = {
        ticket_id:
          typeof ev.data["ticket_id"] === "string"
            ? ev.data["ticket_id"]
            : (s.ticketId ?? ""),
        final_status: (ev.data["final_status"] as TicketStatus) ?? "done",
        rounds: typeof ev.data["rounds"] === "number" ? ev.data["rounds"] : 0,
        approved: ev.data["approved"] === true,
        branch,
      };
      return {
        ...s,
        events,
        status: "done",
        lastResult: result,
        pendingQuestion: null,
        questionExpireA: null,
        branch,
      };
    }
    case "error":
      return {
        ...s,
        events,
        status: "error",
        errorMessage:
          typeof ev.data["message"] === "string"
            ? ev.data["message"]
            : "Pipeline error",
      };
    case "agent_question":
      return {
        ...s,
        events,
        pendingQuestion:
          typeof ev.data["question"] === "string" ? ev.data["question"] : null,
        questionExpireA:
          typeof ev.data["expire_a"] === "string" ? ev.data["expire_a"] : null,
      };
    case "queue_progress":
      // Un nouveau ticket commence. Une file est **un** run (ADR-041), donc un
      // seul état accumulé : sans remise à zéro, les drapeaux dérivés de
      // `events` restaient vrais depuis le ticket d'avant, et le bloc reviewer
      // du précédent s'affichait sous le codeur du suivant — verdict
      // `APPROVED` compris, sur un ticket que personne n'avait encore relu
      // (ticket-180).
      //
      // Ce qui appartient au **run** survit : l'avancement de la file, le
      // quota, la branche. Ce qui appartient au **ticket** repart de zéro.
      return {
        ...INITIAL,
        status: "running",
        quota: s.quota,
        branch: s.branch,
        maxRounds: s.maxRounds,
        ticketId: ev.ticket_id || s.ticketId,
        queue: {
          index: Number(ev.data["index"] ?? 0),
          total: Number(ev.data["total"] ?? 0),
        },
      };
    case "quota_updated":
      // Le quota d'abonnement est la ressource réellement finie : l'afficher
      // évite d'être coupé sans comprendre pourquoi (ticket-054).
      return { ...s, events, quota: ev.data as unknown as QuotaState };

    default:
      return { ...s, events };
  }
}
