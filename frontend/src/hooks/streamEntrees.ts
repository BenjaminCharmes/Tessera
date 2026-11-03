/**
 * Les entrées du fil chronologique d'un run, et le dernier outil appelé.
 *
 * Sorties de `streamState.ts` pour tenir le plafond de longueur (ticket-545) :
 * `streamState` les ré-exporte, les importeurs n'ont rien à changer.
 */
import { verdictDeData } from "../components/FilDuRun/verdict";
import type { VerdictReviewer } from "../components/FilDuRun/verdict";
import type { AgentRole, OrchestratorEvent } from "../types/api";

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
  /** Verdict du reviewer, champ `verdict` de `agent_done` (ticket-614). Absent avant ce ticket. */
  verdict?: VerdictReviewer;
}

/** Le passage, refermé par l'`agent_done` dont `data` est donné : contenu, durée et verdict. */
export function passageTermine(passage: PassageAgent, data: Record<string, unknown>): PassageAgent {
  const duree = data["duration_ms"];
  return {
    ...passage,
    isDone: true,
    content: typeof data["content"] === "string" ? data["content"] : "",
    duration_ms: typeof duree === "number" ? duree : undefined,
    verdict: verdictDeData(data),
  };
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

/** Le dernier appel d'outil d'un agent, tel que `agent_tool_use` l'a annoncé (ticket-601). */
export interface DernierOutil {
  agent: AgentRole | null;
  outil: string;
  entree: Record<string, unknown>;
  /** Horodatage de l'événement : la bulle du Bureau s'efface dix secondes plus tard. */
  horodatage: string;
}

/** L'outil qu'un `agent_tool_use` annonce, ou null quand l'événement n'en nomme aucun (ticket-601). */
export function dernierOutilDe(ev: OrchestratorEvent): DernierOutil | null {
  const outil = ev.data["tool"];
  if (typeof outil !== "string" || outil === "") return null;
  const brut = ev.data["input"];
  const entree =
    typeof brut === "object" && brut !== null && !Array.isArray(brut)
      ? (brut as Record<string, unknown>)
      : {};
  return { agent: ev.agent, outil, entree, horodatage: ev.timestamp };
}
