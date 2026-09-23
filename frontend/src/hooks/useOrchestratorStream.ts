import { useRef, useState } from "react";
import { api } from "../lib/api";
import { wsUrl } from "../lib/ws";
import type {
  AgentRole,
  OrchestratorEvent,
  RunRequest,
  PipelineResult,
  QuotaState,
  TicketStatus,
} from "../types/api";

type StreamStatus = "idle" | "connecting" | "running" | "done" | "error";

interface StreamState {
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
  /** Avancement d'une file de tickets, ou null hors file (ticket-074). */
  queue: { index: number; total: number } | null;
  /**
   * Branche du run en cours, annoncée par `branch_created` puis confirmée par
   * `pipeline_done`. Sans elle, `TicketActivity` proposait de « lancer
   * d'abord le pipeline » après un run approuvé (ticket-123).
   */
  branch: string | null;
  /** Nombre de tours du run, quand le backend le dit ; null sinon. */
  maxRounds: number | null;
}

export interface UseOrchestratorStreamResult extends StreamState {
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

const INITIAL: StreamState = {
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
  queue: null,
  branch: null,
  maxRounds: null,
};

function applyEvent(s: StreamState, ev: OrchestratorEvent): StreamState {
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
      };
    case "agent_token":
      return {
        ...s,
        events,
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
      };
    case "queue_progress":
      return {
        ...s,
        events,
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

export function useOrchestratorStream(
  projectId: string | null,
): UseOrchestratorStreamResult {
  const [state, setState] = useState<StreamState>(INITIAL);
  const wsRef = useRef<WebSocket | null>(null);
  const ticketIdRef = useRef<string | null>(null);
  const queueRef = useRef<string[] | null>(null);
  // Le mode autonome : l'IDE choisit lui-même le prochain ticket, par
  // priorité et dépendances (ticket-089). `null` quand on ne l'utilise pas.
  const autonomeRef = useRef<{ depuisGithub: boolean } | null>(null);
  const isDoneRef = useRef(false);
  // L'identifiant du run observé : toute réponse au dialogue le nomme, parce
  // que le canal en porte plusieurs (ticket-128).
  const runIdRef = useRef<string | null>(null);

  function closeWs() {
    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onmessage = null;
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.close();
      wsRef.current = null;
    }
  }

  /**
   * Ouvre le canal d'observation, sans rien lancer.
   *
   * La socket ne porte plus le run depuis ticket-128 : elle ne fait que
   * regarder. C'est ce qui rend la reconnexion sûre — rouvrir renvoyait
   * autrefois la commande de démarrage, donc lançait un **nouveau** run. Le
   * 2026-09-17, trois runs sont partis sur un ticket qui échouait vite, sans
   * que personne n'ait recliqué (ticket-068).
   */
  function ouvrirObservation() {
    if (!projectId) return;
    closeWs();

    const ws = new WebSocket(wsUrl("/api/v1/orchestrator/observe"));
    wsRef.current = ws;

    ws.onmessage = (event: MessageEvent) => {
      try {
        const brut = JSON.parse(event.data as string) as OrchestratorEvent & {
          runs?: unknown;
        };
        // L'instantané d'ouverture n'est pas un événement de run.
        if (brut.type === ("snapshot" as never)) return;
        // Le canal porte tous les projets : ne garder que le nôtre.
        if (brut.project_id && brut.project_id !== projectId) return;
        if (brut.run_id) runIdRef.current = brut.run_id;
        if (brut.type === "run_closed") isDoneRef.current = true;
        setState((s) => applyEvent(s, brut));
      } catch {
        // ignore malformed frames
      }
    };

    ws.onclose = () => {
      if (isDoneRef.current) return;
      // Se rattacher ne relance rien : on peut le dire sans alarmer.
      setState((s) => ({
        ...s,
        status: "error",
        errorMessage:
          "Connexion au canal d'observation perdue. Le run continue côté " +
          "serveur : rouvre la vue pour le retrouver.",
      }));
    };
  }

  function demarrer(corps: RunRequest, ticketId: string) {
    if (!projectId) return;
    setState((s) => ({
      ...s,
      status: "connecting",
      ticketId,
      currentTokens: "",
      currentAgent: null,
      currentRound: 0,
      errorMessage: null,
    }));
    ouvrirObservation();
    void api.orchestrator
      .run(corps)
      .then(({ run_id }) => {
        runIdRef.current = run_id;
      })
      .catch((erreur: unknown) => {
        isDoneRef.current = true;
        setState((s) => ({
          ...s,
          status: "error",
          errorMessage:
            erreur instanceof Error ? erreur.message : "Lancement refusé",
        }));
      });
  }

  function send(payload: Record<string, string>) {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN && runIdRef.current) {
      ws.send(JSON.stringify({ ...payload, run_id: runIdRef.current }));
    }
  }

  function answer(text: string) {
    send({ type: "answer", text });
    // La question disparaît dès l'envoi : le backend ne réémet rien, et
    // laisser le formulaire à l'écran donnerait à croire que la réponse
    // n'est pas partie.
    setState((s) => ({ ...s, pendingQuestion: null }));
  }

  function interject(text: string) {
    send({ type: "interject", text });
  }

  function stop() {
    send({ type: "stop", text: "" });
  }

  function connectAutonome(options: { depuisGithub: boolean }) {
    ticketIdRef.current = null;
    queueRef.current = null;
    autonomeRef.current = options;
    isDoneRef.current = false;
    setState({ ...INITIAL, status: "connecting" });
    demarrer(
      {
        project_id: projectId ?? "",
        mode: "autonomous",
        depuis_github: options.depuisGithub,
      },
      "",
    );
  }

  function connectQueue(ticketIds: string[]) {
    if (ticketIds.length === 0) return;
    ticketIdRef.current = ticketIds[0] ?? null;
    queueRef.current = ticketIds;
    autonomeRef.current = null;
    isDoneRef.current = false;
    setState({ ...INITIAL, ticketId: ticketIds[0] ?? null });
    demarrer(
      { project_id: projectId ?? "", mode: "queue", ticket_ids: ticketIds },
      ticketIds[0] ?? "",
    );
  }

  function connect(ticketId: string) {
    ticketIdRef.current = ticketId;
    queueRef.current = null;
    autonomeRef.current = null;
    isDoneRef.current = false;
    setState({ ...INITIAL, ticketId });
    demarrer(
      { project_id: projectId ?? "", mode: "single", ticket_id: ticketId },
      ticketId,
    );
  }

  function disconnect() {
    isDoneRef.current = true;
    closeWs();
    setState((s) => ({ ...s, status: "idle" }));
  }

  function clear() {
    isDoneRef.current = true;
    ticketIdRef.current = null;
    queueRef.current = null;
    autonomeRef.current = null;
    closeWs();
    setState(INITIAL);
  }

  return {
    ...state,
    connect,
    connectQueue,
    connectAutonome,
    disconnect,
    clear,
    answer,
    interject,
    stop,
  };
}
