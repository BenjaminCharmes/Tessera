/**
 * Ce que `external_wait` et `conflict_resolution` posent dans l'état d'un run
 * (ticket-564). Pur, comme `applyEvent` : se teste sans socket.
 */
import type { OrchestratorEvent } from "../types/api";
import type { StreamState } from "./streamState";

/** Données de `external_wait` : un agent attend un événement extérieur au run. */
export interface DonneesExternalWait {
  reason: string;
  waiting: boolean;
  ticket: string;
  pr_number: number | null;
}

/** Données de `conflict_resolution` : le résolveur travaille, puis rend son issue. */
export interface DonneesConflictResolution {
  phase: "started" | "ended";
  files: string[];
  outcome: "resolved" | "cancelled" | null;
}

/** Une attente extérieure en cours : sa raison, et la PR attendue quand on la connaît. */
export interface AttenteExterieure {
  raison: string;
  pr: number | null;
}

function fichiersDe(data: Record<string, unknown>): string[] {
  const brut = data["files"];
  return Array.isArray(brut) ? brut.filter((f): f is string => typeof f === "string") : [];
}

/** `waiting: true` pose l'attente ; toute autre valeur la retire. */
export function appliquerAttente(
  ev: OrchestratorEvent,
): Pick<StreamState, "attenteExterieure"> {
  if (ev.data["waiting"] !== true) return { attenteExterieure: null };
  const raison = ev.data["reason"];
  const pr = ev.data["pr_number"];
  return {
    attenteExterieure: {
      raison: typeof raison === "string" ? raison : "",
      pr: typeof pr === "number" ? pr : null,
    },
  };
}

/**
 * `answer_ack` : le backend accuse réception de la réponse. « transmitted » : elle
 * est parvenue à l'agent, la question disparaît. « deposited » : aucune question
 * n'attendait, la réponse est en boîte aux lettres — la question éventuelle reste
 * affichée.
 */
export function appliquerAccuse(
  s: StreamState,
  ev: OrchestratorEvent,
): Pick<StreamState, "pendingQuestion" | "questionExpireA" | "answerAck"> {
  const outcome = ev.data["outcome"];
  const transmise = outcome === "transmitted";
  return {
    pendingQuestion: transmise ? null : s.pendingQuestion,
    questionExpireA: transmise ? null : s.questionExpireA,
    answerAck: transmise || outcome === "deposited" ? outcome : null,
  };
}

/** Le dernier repli de provider d'un run (ticket-597) : qui a été tenté, qui a répondu, et quand. */
export interface RepliDeProvider {
  role: string;
  tente: string;
  utilise: string;
  modele: string;
  /** Instant de l'événement, en ms depuis l'époque : les RH en tirent leur délai de 20 s. */
  a: number;
}

function texteDe(data: Record<string, unknown>, cle: string): string {
  const v = data[cle];
  return typeof v === "string" ? v : "";
}

/**
 * `provider_fallback` : le rôle repasse sur son provider de repli. Sans rôle
 * lisible ou sans horodatage valide, rien n'est posé — la salle des RH n'a
 * alors rien de vrai à montrer (ADR-058).
 */
export function appliquerRepli(ev: OrchestratorEvent): Pick<StreamState, "repli"> | null {
  const role = texteDe(ev.data, "role");
  const a = Date.parse(ev.timestamp);
  if (role === "" || Number.isNaN(a)) return null;
  return {
    repli: {
      role,
      tente: texteDe(ev.data, "tente"),
      utilise: texteDe(ev.data, "utilise"),
      modele: texteDe(ev.data, "modele"),
      a,
    },
  };
}

/** `started` pose les fichiers du conflit ; `ended` les retire. */
export function appliquerConflit(
  ev: OrchestratorEvent,
): Pick<StreamState, "conflitEnCours"> {
  if (ev.data["phase"] === "started") return { conflitEnCours: fichiersDe(ev.data) };
  return { conflitEnCours: null };
}
