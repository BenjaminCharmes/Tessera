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

/**
 * Un passage d'un agent dans le fil chronologique du run (ticket-222).
 *
 * Chaque `agent_started` crée une entrée. Rien n'est écrasé : au tour 2,
 * le passage du reviewer au tour 1 reste visible dans `entries`.
 */
export interface PassageAgent {
  /** Discriminant du type d'entrée dans le fil (ticket-257). */
  genre: "agent";
  /** Clé unique pour React : `${agent}-${index}`. */
  id: string;
  agent: AgentRole;
  round: number;
  /** Tokens reçus en direct (codeur uniquement). Vide après reconnexion. */
  tokens: string;
  /** Contenu issu de `agent_done` : verdict ou compte rendu. */
  content: string;
  isDone: boolean;
  /** Durée de l'appel en ms, remontée par `agent_done`. Absente si le backend ne l'envoie pas. */
  duration_ms?: number;
}

/**
 * Entrée de l'audit sécurité dans le fil chronologique (ticket-257).
 *
 * Ajoutée par `security_audit_done` : toujours terminée, jamais modifiée.
 */
export interface EntreeSecurite {
  genre: "securite";
  id: string;
  round: number;
  verdict: string;
  summary: string;
  issues_count: number;
  reason: string;
  isDone: true;
}

/**
 * Entrée du validateur dans le fil chronologique (ticket-257).
 *
 * Ajoutée par `validation_done` : toujours terminée, jamais modifiée.
 * `criteria` porte le détail critère par critère, avec son résultat et sa note.
 */
export interface EntreeValidateur {
  genre: "validateur";
  id: string;
  round: number;
  verdict: string;
  feedback: string;
  criteria: { criterion: string; passed: boolean; note: string }[];
  isDone: true;
}

/**
 * Entrée du testeur dans le fil chronologique (ticket-321).
 *
 * Ajoutée par `test_result` : toujours terminée, jamais modifiée.
 * `errors` porte les lignes d'erreur extraites par le backend (au plus 5).
 */
export interface EntreeTesteur {
  genre: "testeur";
  id: string;
  round: number;
  passed: boolean;
  output_summary: string;
  errors: string[];
  isDone: true;
}

/** Une entrée du fil chronologique : agent, sécurité, validateur ou testeur. */
export type EntreeFil = PassageAgent | EntreeSecurite | EntreeValidateur | EntreeTesteur;

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

/** Ajoute une étape à la liste des étapes en cours (sans doublon). */
function addEtapeEnCours(etapesEnCours: string[], etape: string): string[] {
  if (etapesEnCours.includes(etape)) return etapesEnCours;
  return [...etapesEnCours, etape];
}

/** Retire une étape de la liste des étapes en cours. */
function removeEtapeEnCours(etapesEnCours: string[], etape: string): string[] {
  return etapesEnCours.filter((e) => e !== etape);
}

export function applyEvent(s: StreamState, ev: OrchestratorEvent): StreamState {
  const events = [...s.events, ev];
  // ticketEvents repart de zéro à chaque queue_progress : StageStrip voit
  // les étapes du ticket en cours, pas celles du ticket précédent (ticket-313).
  const ticketEvents =
    ev.type === "queue_progress" ? [ev] : [...s.ticketEvents, ev];
  switch (ev.type) {
    case "agent_started": {
      const round =
        typeof ev.data["round"] === "number" ? ev.data["round"] : s.currentRound;
      const agent = ev.agent;
      // L'étape se déduit du rôle : codeur = production, reviewer = revue.
      const etapeAgent =
        agent === "codeur" ? "production"
        : agent === "reviewer" ? "revue"
        : s.etape;
      // ticket-290 : suivre les étapes en cours pour le parallélisme.
      const etapeEnCoursToAdd =
        agent === "codeur" ? "production"
        : agent === "reviewer" ? "revue"
        : null;
      const newEtapesEnCours = etapeEnCoursToAdd
        ? addEtapeEnCours(s.etapesEnCours, etapeEnCoursToAdd)
        : s.etapesEnCours;
      const newEntry: PassageAgent | null = agent
        ? {
            genre: "agent",
            id: `${agent}-${s.entries.length}`,
            agent,
            round,
            tokens: "",
            content: "",
            isDone: false,
          }
        : null;
      return {
        ...s,
        events,
        ticketEvents,
        status: "running",
        currentAgent: agent,
        currentRound: round,
        etape: etapeAgent,
        etapesEnCours: newEtapesEnCours,
        maxRounds:
          typeof ev.data["max_rounds"] === "number"
            ? ev.data["max_rounds"]
            : s.maxRounds,
        currentTokens: "",
        outils: 0,
        entries: newEntry ? [...s.entries, newEntry] : s.entries,
      };
    }
    case "branch_created":
      return {
        ...s,
        events,
        ticketEvents,
        branch:
          typeof ev.data["branch"] === "string" ? ev.data["branch"] : s.branch,
      };
    case "agent_done": {
      // Sans cela `currentAgent` restait figé sur le dernier agent démarré :
      // ses points de chargement continuaient de rebondir alors qu'il avait
      // rendu son verdict (ticket-073).
      const doneAgent = ev.agent;
      const doneContent =
        typeof ev.data["content"] === "string" ? ev.data["content"] : "";
      const doneDurationMs =
        typeof ev.data["duration_ms"] === "number" ? ev.data["duration_ms"] : undefined;
      // Marquer le dernier passage non terminé de cet agent comme terminé.
      // Seules les entrées de genre "agent" ont un champ `agent`.
      const lastUnfinishedIdx = s.entries.reduceRight(
        (found, e, i) =>
          found === -1 && e.genre === "agent" && e.agent === doneAgent && !e.isDone ? i : found,
        -1,
      );
      const updatedEntries =
        lastUnfinishedIdx >= 0
          ? s.entries.map((e, i) => {
              if (i !== lastUnfinishedIdx || e.genre !== "agent") return e;
              return { ...e, isDone: true, content: doneContent, duration_ms: doneDurationMs };
            })
          : s.entries;
      // ticket-290 : retirer l'étape de la liste des étapes en cours.
      const etapeAgentDone =
        doneAgent === "codeur" ? "production"
        : doneAgent === "reviewer" ? "revue"
        : null;
      const etapesEnCoursApresDone = etapeAgentDone
        ? removeEtapeEnCours(s.etapesEnCours, etapeAgentDone)
        : s.etapesEnCours;
      return {
        ...s,
        events,
        ticketEvents,
        currentAgent: s.currentAgent === doneAgent ? null : s.currentAgent,
        etapesEnCours: etapesEnCoursApresDone,
        coutUsd:
          s.coutUsd +
          (typeof ev.data["cost_usd"] === "number" ? ev.data["cost_usd"] : 0),
        appels: s.appels + 1,
        entries: updatedEntries,
      };
    }
    case "agent_token":
    case "agent_tool_use": {
      // L'agent a repris — sur réponse, ou seul passé le délai (ADR-025).
      // Garder la question ferait répondre à un agent qui n'écoute plus ;
      // le registre l'efface déjà, un client en direct ne le faisait pas
      // (ticket-186).
      // L'accusé de réception s'efface aussi : l'agent a pris la main, le
      // message est consommé (ticket-320).
      const token =
        ev.type === "agent_token" && ev.agent === "codeur"
          ? (typeof ev.data["token"] === "string" ? ev.data["token"] : "")
          : "";
      // Ajouter le token au dernier passage non terminé du codeur.
      // Seules les entrées de genre "agent" ont un champ `agent`.
      let tokenEntries = s.entries;
      if (token) {
        const lastCodeurIdx = s.entries.reduceRight(
          (found, e, i) =>
            found === -1 && e.genre === "agent" && e.agent === "codeur" && !e.isDone ? i : found,
          -1,
        );
        if (lastCodeurIdx >= 0) {
          tokenEntries = s.entries.map((e, i) => {
            if (i !== lastCodeurIdx || e.genre !== "agent") return e;
            return { ...e, tokens: e.tokens + token };
          });
        }
      }
      return {
        ...s,
        events,
        ticketEvents,
        pendingQuestion: null,
        questionExpireA: null,
        answerAck: null,
        outils: ev.type === "agent_tool_use" ? s.outils + 1 : s.outils,
        currentTokens:
          ev.agent === "codeur"
            ? s.currentTokens +
              (typeof ev.data["token"] === "string" ? ev.data["token"] : "")
            : s.currentTokens,
        entries: tokenEntries,
      };
    }
    case "test_result": {
      // Le testeur ajoute une entrée dans le fil après chaque passage du codeur (ticket-321).
      const rawErrors = Array.isArray(ev.data["errors"]) ? ev.data["errors"] : [];
      const testEntry: EntreeTesteur = {
        genre: "testeur",
        id: `testeur-${s.entries.length}`,
        round: s.currentRound,
        passed: ev.data["passed"] === true,
        output_summary:
          typeof ev.data["output_summary"] === "string" ? ev.data["output_summary"] : "",
        errors: rawErrors.filter((e: unknown): e is string => typeof e === "string"),
        isDone: true,
      };
      return {
        ...s,
        events,
        ticketEvents,
        entries: [...s.entries, testEntry],
      };
    }
    case "security_audit_done": {
      // L'audit ajoute une entrée dans le fil, visible à côté des agents (ticket-257).
      const auditEntry: EntreeSecurite = {
        genre: "securite",
        id: `securite-${s.entries.length}`,
        round: s.currentRound,
        verdict: typeof ev.data["verdict"] === "string" ? ev.data["verdict"] : "",
        summary: typeof ev.data["summary"] === "string" ? ev.data["summary"] : "",
        issues_count: typeof ev.data["issues_count"] === "number" ? ev.data["issues_count"] : 0,
        reason: typeof ev.data["reason"] === "string" ? ev.data["reason"] : "",
        isDone: true,
      };
      return {
        ...s,
        events,
        ticketEvents,
        entries: [...s.entries, auditEntry],
        etapesEnCours: removeEtapeEnCours(s.etapesEnCours, "securite"),
      };
    }
    case "validation_done": {
      // La validation ajoute une entrée dans le fil, critère par critère (ticket-257).
      const rawCriteria = Array.isArray(ev.data["criteria"]) ? ev.data["criteria"] : [];
      const criteria = rawCriteria.map((c: unknown) => {
        const cr = c as Record<string, unknown>;
        return {
          criterion: typeof cr["criterion"] === "string" ? cr["criterion"] : "",
          passed: cr["passed"] === true,
          note: typeof cr["note"] === "string" ? cr["note"] : "",
        };
      });
      const validEntry: EntreeValidateur = {
        genre: "validateur",
        id: `validateur-${s.entries.length}`,
        round: s.currentRound,
        verdict: typeof ev.data["verdict"] === "string" ? ev.data["verdict"] : "",
        feedback: typeof ev.data["feedback"] === "string" ? ev.data["feedback"] : "",
        criteria,
        isDone: true,
      };
      return {
        ...s,
        events,
        ticketEvents,
        entries: [...s.entries, validEntry],
        etapesEnCours: removeEtapeEnCours(s.etapesEnCours, "validation"),
      };
    }
    case "security_audit_started":
      return {
        ...s,
        events,
        ticketEvents,
        etape: "securite",
        etapesEnCours: addEtapeEnCours(s.etapesEnCours, "securite"),
      };
    case "validation_started":
      return {
        ...s,
        events,
        ticketEvents,
        etape: "validation",
        etapesEnCours: addEtapeEnCours(s.etapesEnCours, "validation"),
      };
    case "documentation_started":
      return {
        ...s,
        events,
        ticketEvents,
        etape: "documentation",
        etapesEnCours: addEtapeEnCours(s.etapesEnCours, "documentation"),
      };
    case "livraison_started":
      return {
        ...s,
        events,
        ticketEvents,
        etape: "livraison",
        etapesEnCours: addEtapeEnCours(s.etapesEnCours, "livraison"),
      };
    case "pipeline_done": {
      const branch =
        typeof ev.data["branch"] === "string" ? ev.data["branch"] : s.branch;
      // Le ticket_id est au premier niveau de l'événement (ev.ticket_id) ;
      // ev.data["ticket_id"] est un doublon de confort, pas toujours présent.
      const result: PipelineResult = {
        ticket_id:
          ev.ticket_id ||
          (typeof ev.data["ticket_id"] === "string"
            ? ev.data["ticket_id"]
            : "") ||
          s.ticketId ||
          "",
        final_status: (ev.data["final_status"] as TicketStatus) ?? "done",
        rounds: typeof ev.data["rounds"] === "number" ? ev.data["rounds"] : 0,
        approved: ev.data["approved"] === true,
        branch,
      };
      return {
        ...s,
        events,
        ticketEvents,
        status: "done",
        lastResult: result,
        etape: null,
        etapesEnCours: [],
        pendingQuestion: null,
        questionExpireA: null,
        branch,
      };
    }
    case "ticket_status_changed":
      // Quand le backend change le ticket courant (file), il inclut le titre
      // dans les données de l'événement pour les observateurs connectés (ticket-286).
      return {
        ...s,
        events,
        ticketEvents,
        ticketTitre:
          typeof ev.data["ticket_titre"] === "string"
            ? ev.data["ticket_titre"]
            : s.ticketTitre,
      };
    case "livraison_done": {
      const prNumber =
        typeof ev.data["pr_number"] === "number" ? ev.data["pr_number"] : null;
      return {
        ...s,
        events,
        ticketEvents,
        etapesEnCours: removeEtapeEnCours(s.etapesEnCours, "livraison"),
        livraisonPrNumber: prNumber ?? s.livraisonPrNumber,
      };
    }
    case "ci_merge_done": {
      const merged = ev.data["merged"] === true;
      const arret =
        typeof ev.data["arret"] === "string" ? ev.data["arret"] : null;
      return { ...s, events, ticketEvents, ciMerge: { merged, arret } };
    }
    case "doc_updated":
    case "documentation_failed":
      return { ...s, events, ticketEvents, etapesEnCours: removeEtapeEnCours(s.etapesEnCours, "documentation") };
    case "run_closed":
      // Le run est définitivement terminé : livraison et documentation sont finies.
      // Le bouton « Fermer » n'apparaît qu'ici (ticket-267). L'étape active se
      // remet à null : livraison ou doc ne clignotent plus après la clôture (ticket-279).
      return { ...s, events, ticketEvents, runClosed: true, etape: null, etapesEnCours: [] };
    case "error":
      return {
        ...s,
        events,
        ticketEvents,
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
        ticketEvents,
        pendingQuestion:
          typeof ev.data["question"] === "string" ? ev.data["question"] : null,
        questionExpireA:
          typeof ev.data["expire_a"] === "string" ? ev.data["expire_a"] : null,
        // Une nouvelle question efface l'accusé de la réponse précédente.
        answerAck: null,
      };
    case "answer_ack": {
      // Le backend accuse réception de la réponse (ticket-320).
      const outcome = ev.data["outcome"];
      return {
        ...s,
        events,
        ticketEvents,
        answerAck:
          outcome === "transmitted" || outcome === "deposited"
            ? outcome
            : null,
      };
    }
    case "queue_progress":
      // Un nouveau ticket commence. Une file est **un** run (ADR-041), donc un
      // seul état accumulé : sans remise à zéro, les drapeaux dérivés de
      // `events` restaient vrais depuis le ticket d'avant, et le bloc reviewer
      // du précédent s'affichait sous le codeur du suivant — verdict
      // `APPROVED` compris, sur un ticket que personne n'avait encore relu
      // (ticket-180).
      //
      // Ce qui appartient au **run** survit : les événements bruts (Pipeline
      // log), l'avancement de la file, le quota, la branche.
      // Ce qui appartient au **ticket** repart de zéro : `entries`, `currentAgent`,
      // `currentRound` — l'affichage du tableau d'agents.
      // Les événements bruts sont gardés pour que le Pipeline log montre
      // l'historique complet d'une file (ticket-283).
      return {
        ...INITIAL,
        status: "running",
        events: [...s.events, ev],
        // ticketEvents = [ev] pour ce cas (ternaire en tête de applyEvent).
        ticketEvents,
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
      return { ...s, events, ticketEvents, quota: ev.data as unknown as QuotaState };

    default:
      return { ...s, events, ticketEvents };
  }
}
