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

/** `started` pose les fichiers du conflit ; `ended` les retire. */
export function appliquerConflit(
  ev: OrchestratorEvent,
): Pick<StreamState, "conflitEnCours"> {
  if (ev.data["phase"] === "started") return { conflitEnCours: fichiersDe(ev.data) };
  return { conflitEnCours: null };
}
