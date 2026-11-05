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
} from "../types/api";
import { boundEvents } from "./boundEvents";
import { appliquerAgent, appliquerToken } from "./streamAgents";
import { appliquerAnomalie } from "./streamAnomalies";
import { appliquerDialogue } from "./streamDialogue";
import type { DernierOutil, EntreeFil } from "./streamEntrees";
import { appliquerEtape } from "./streamEtapes";
import { appliquerRun } from "./streamRun";
import { appliquerVerdict } from "./streamVerdicts";
import type { AttenteExterieure, RepliDeProvider } from "./streamAttente";

export { MAX_EVENTS } from "./boundEvents";

export type {
  DernierOutil,
  EntreeAnomalie,
  EntreeFil,
  EntreeSecurite,
  EntreeTesteur,
  EntreeValidateur,
  PassageAgent,
} from "./streamEntrees";

export type StreamStatus = "idle" | "connecting" | "running" | "done" | "error";

export interface StreamState {
  status: StreamStatus;
  ticketId: string | null;
  /** Titre lisible du ticket en cours, reçu de l'instantané ou des événements (ticket-286). */
  ticketTitre: string | null;
  events: OrchestratorEvent[];
  /**
   * Événements du ticket en cours seulement (ticket-313).
   *
   * `events` garde tout l'historique d'un run de file (Pipeline log) ; cette
   * liste repart de zéro à chaque `queue_progress`, de sorte que `StageStrip`
   * et les autres dérivations voient les étapes du ticket en cours et non celles
   * du ticket précédent.
   */
  ticketEvents: OrchestratorEvent[];
  currentAgent: AgentRole | null;
  currentRound: number;
  currentTokens: string;
  lastResult: PipelineResult | null;
  errorMessage: string | null;
  /** Étape du pipeline en cours (ticket-256) : "production", "securite", "revue",
   *  "validation", "documentation", "livraison". Null hors run ou après pipeline_done. */
  etape: string | null;
  /** Étapes actives en parallèle (ticket-290). Vide hors run. */
  etapesEnCours: string[];
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
  /** Fil chronologique des passages d'agents, d'audits et de validations (ticket-222, ticket-257). */
  entries: EntreeFil[];
  /**
   * Vrai après `run_closed` : la livraison et la documentation sont terminées,
   * le projet est libéré. Entre `pipeline_done` et `run_closed`, le run est
   * approuvé mais la livraison tourne encore (ticket-267).
   */
  runClosed: boolean;
  /**
   * Numéro de PR ouverte lors de la livraison (phase 1), disponible dès
   * `livraison_done`. Null si aucune PR n'a été ouverte (ticket-308).
   */
  livraisonPrNumber: number | null;
  /**
   * Résultat du merge CI, disponible après `ci_merge_done` (ticket-308).
   * Null tant que le watcher n'a pas rendu son verdict.
   */
  ciMerge: { merged: boolean; arret: string | null } | null;
  /**
   * Accusé de réception de la dernière réponse envoyée (ticket-320).
   * « transmitted » : la réponse est parvenue à la question en attente.
   * « deposited » : aucune question n'attendait, la réponse a été déposée
   * en boîte aux lettres pour le prochain tour d'agent.
   * Null avant tout envoi, ou après que l'agent a repris.
   */
  answerAck: "transmitted" | "deposited" | null;
  /** Horodatage du dernier événement reçu, tokens compris (ticket-549). */
  dernierEvenementA: string | null;
  /** Attente d'un événement extérieur (`external_wait`), tant qu'elle dure (ticket-564). */
  attenteExterieure: AttenteExterieure | null;
  /** Fichiers du conflit que le résolveur travaille, entre `started` et `ended` (ticket-564). */
  conflitEnCours: string[] | null;
  /** Dernier `provider_fallback` du run, relié par son projet (ticket-597). Non persisté : un F5 l'efface. */
  repli: RepliDeProvider | null;
  /** Dernier `agent_tool_use` du ticket en cours (ticket-601). Non persisté : un F5 l'efface. */
  dernierOutil: DernierOutil | null;
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
  ticketTitre: null,
  events: [],
  ticketEvents: [],
  currentAgent: null,
  currentRound: 0,
  currentTokens: "",
  lastResult: null,
  errorMessage: null,
  etape: null,
  etapesEnCours: [],
  quota: null,
  pendingQuestion: null,
  questionExpireA: null,
  queue: null,
  branch: null,
  maxRounds: null,
  coutUsd: 0,
  appels: 0,
  outils: 0,
  entries: [],
  runClosed: false,
  livraisonPrNumber: null,
  ciMerge: null,
  answerAck: null,
  dernierEvenementA: null,
  attenteExterieure: null,
  conflitEnCours: null,
  repli: null,
  dernierOutil: null,
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
    ticketTitre: run.ticket_titre ?? null,
    currentAgent: run.agent,
    currentRound: run.tour || INITIAL.currentRound,
    // L'étape en cours est dans l'instantané depuis ticket-255 (ticket-256).
    etape: run.etape ?? null,
    // ticket-290 : liste des étapes actives en parallèle. Repli sur [etape] si absent.
    etapesEnCours: run.etapes_en_cours ?? (run.etape ? [run.etape] : []),
    pendingQuestion: run.question ?? null,
    questionExpireA: run.question_expire_a ?? null,
    // Un F5 retrouve le cumul depuis l'instantané (ticket-197).
    coutUsd: run.cout_usd,
    appels: run.appels ?? 0,
    outils: run.outils ?? 0,
    // Les entrées se reconstruisent au fil des événements après reconnexion.
    entries: [],
  };
}

/**
 * Vide les accumulateurs de tokens avant un rejeu côté serveur (ticket-313).
 *
 * À chaque `subscribe`, le backend renvoie le tampon de texte du run. Si
 * l'état accumulé contient déjà ces tokens (visite précédente), les ajouter
 * de nouveau doublerait le texte affiché. Vider les tokens des entrées non
 * terminées avant le rejeu les remet à zéro : le rejeu les remplit depuis
 * le début, et le résultat est identique à la première visite.
 *
 * Les entrées `isDone: true` gardent leur `content` (issu de `agent_done`) ;
 * seul le streaming en direct, stocké dans `tokens`, est effacé.
 */
export function clearTokensForReplay(s: StreamState): StreamState {
  return {
    ...s,
    currentTokens: "",
    entries: s.entries.map((e) => {
      if (e.genre === "agent" && !e.isDone) {
        return { ...e, tokens: "" };
      }
      return e;
    }),
  };
}

/** Applique l'événement et note quand il est arrivé, jeton d'agent compris (ticket-549). */
export function applyEvent(s: StreamState, ev: OrchestratorEvent): StreamState {
  // Le constat du détecteur ne rompt pas le silence qu'il signale (ADR-078).
  const dernier = ev.type === "run_anomaly" ? s.dernierEvenementA : ev.timestamp;
  return { ...appliquerEvenement(s, ev), dernierEvenementA: dernier };
}

/**
 * Un nouveau ticket commence. Une file est **un** run (ADR-041), donc un seul
 * état accumulé : sans remise à zéro, les drapeaux dérivés de `events`
 * restaient vrais depuis le ticket d'avant, et le bloc reviewer du précédent
 * s'affichait sous le codeur du suivant (ticket-180).
 *
 * Ce qui appartient au **run** survit : événements bruts (Pipeline log,
 * ticket-283), avancement de la file, quota, branche, repli (ticket-597).
 * Ce qui appartient au **ticket** repart de zéro : `entries`, `currentAgent`,
 * `currentRound`.
 */
function appliquerFile(
  s: StreamState,
  ev: OrchestratorEvent,
  events: OrchestratorEvent[],
): StreamState {
  return {
    ...INITIAL,
    status: "running",
    events,
    ticketEvents: [ev],
    quota: s.quota,
    branch: s.branch,
    maxRounds: s.maxRounds,
    repli: s.repli,
    ticketId: ev.ticket_id || s.ticketId,
    queue: {
      index: Number(ev.data["index"] ?? 0),
      total: Number(ev.data["total"] ?? 0),
    },
  };
}

/** Le morceau d'état que la famille de l'événement produit ; vide si aucune ne le connaît. */
function morceauDe(s: StreamState, ev: OrchestratorEvent): Partial<StreamState> {
  return (
    appliquerAgent(s, ev) ??
    appliquerEtape(s, ev) ??
    appliquerVerdict(s, ev) ??
    appliquerRun(s, ev) ??
    appliquerAnomalie(s, ev) ??
    appliquerDialogue(s, ev) ??
    {}
  );
}

/** Aiguillage : le jeton et la file ont leur propre chemin, le reste va à sa famille. */
function appliquerEvenement(s: StreamState, ev: OrchestratorEvent): StreamState {
  if (ev.type === "agent_token") return appliquerToken(s, ev);
  const events = boundEvents([...s.events, ev]);
  if (ev.type === "queue_progress") return appliquerFile(s, ev, events);
  // `ticketEvents` repart de zéro à chaque queue_progress (ticket-313).
  return { ...s, events, ticketEvents: [...s.ticketEvents, ev], ...morceauDe(s, ev) };
}
