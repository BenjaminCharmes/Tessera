/**
 * Store externe des états de run — ticket-354.
 *
 * Déplace `etats` hors du state React de `useSupervision`, de sorte qu'un
 * événement d'un run ne redessine que les composants qui affichent ce run.
 *
 * Basé sur `useSyncExternalStore` (React 18), sans bibliothèque externe.
 * ADR-013 reste tenu : pas de Zustand ni de Jotai.
 */
import { useSyncExternalStore } from "react";
import { applyEvent, clearTokensForReplay, INITIAL } from "./streamState";
import type { StreamState, StreamStatus } from "./streamState";
import type { OrchestratorEvent } from "../types/api";

/** Résumé de statut d'un run — sans le `StreamState` complet. */
export interface RunStatus {
  runId: string;
  status: StreamStatus;
  pendingQuestion: string | null;
}

// ---------------------------------------------------------------------------
// État singleton du module — vit en dehors de React.
// ---------------------------------------------------------------------------

let _etats: Record<string, StreamState> = {};
// Snapshot immuable renvoyé par getSnapshot() — remplacé à chaque notify().
let _snapshot: Record<string, StreamState> = {};
// Snapshot de statuts : même référence si aucun statut n'a changé.
let _statusSnapshot: RunStatus[] = [];
const _listeners = new Set<() => void>();

// ---------------------------------------------------------------------------
// Fonctions internes
// ---------------------------------------------------------------------------

function computeStatusSnapshot(
  etats: Record<string, StreamState>,
): RunStatus[] {
  return Object.entries(etats).map(([runId, s]) => ({
    runId,
    status: s.status,
    pendingQuestion: s.pendingQuestion,
  }));
}

function statusesChanged(prev: RunStatus[], next: RunStatus[]): boolean {
  if (prev.length !== next.length) return true;
  for (let i = 0; i < prev.length; i++) {
    const p = prev[i]!;
    const n = next[i]!;
    if (
      p.runId !== n.runId ||
      p.status !== n.status ||
      p.pendingQuestion !== n.pendingQuestion
    ) {
      return true;
    }
  }
  return false;
}

function notify(): void {
  // Nouveau snapshot pour que useSyncExternalStore détecte le changement.
  _snapshot = { ..._etats };
  // Snapshot de statuts : même référence si les statuts n'ont pas bougé.
  const next = computeStatusSnapshot(_etats);
  if (statusesChanged(_statusSnapshot, next)) {
    _statusSnapshot = next;
  }
  for (const listener of _listeners) listener();
}

// ---------------------------------------------------------------------------
// API publique du store
// ---------------------------------------------------------------------------

export const runStore = {
  subscribe(listener: () => void): () => void {
    _listeners.add(listener);
    return () => {
      _listeners.delete(listener);
    };
  },

  /** Snapshot complet — mêmes références par run si ce run n'a pas changé. */
  getSnapshot(): Readonly<Record<string, StreamState>> {
    return _snapshot;
  },

  /** Snapshot de statuts — stable si aucun statut n'a changé (pas à chaque token). */
  getStatusSnapshot(): RunStatus[] {
    return _statusSnapshot;
  },

  /**
   * Applique un lot d'événements en une passe et notifie les abonnés.
   *
   * N'émet qu'une seule notification même pour un lot de 50 événements.
   * `applyEvent` est appelé séquentiellement dans l'ordre du lot.
   */
  appliquer(lot: OrchestratorEvent[]): void {
    let changed = false;
    for (const ev of lot) {
      if (!ev.run_id) continue;
      const prev = _etats[ev.run_id] ?? INITIAL;
      const next = applyEvent(prev, ev);
      if (next !== prev) {
        _etats[ev.run_id] = next;
        changed = true;
      }
    }
    if (changed) notify();
  },

  /** Pose directement l'état d'un run (chargement d'historique, snapshot). */
  set(runId: string, etat: StreamState): void {
    _etats[runId] = etat;
    notify();
  },

  /** Vide les tokens avant un rejeu côté serveur (ticket-313). */
  clearTokens(runId: string): void {
    const etat = _etats[runId];
    if (!etat) return;
    const cleared = clearTokensForReplay(etat);
    if (cleared !== etat) {
      _etats[runId] = cleared;
      notify();
    }
  },

  /** Réinitialise tout le store — réservé aux tests. */
  reset(): void {
    _etats = {};
    _snapshot = {};
    _statusSnapshot = [];
    // Ne notifie pas : l'appelant remonte lui-même.
  },
};

// ---------------------------------------------------------------------------
// Hooks React
// ---------------------------------------------------------------------------

/**
 * Souscrit à l'état d'un seul run.
 *
 * Ne redessine le composant que si l'état de *ce* run a changé — pas quand
 * un autre run reçoit un token.
 */
export function useEtatRun(runId: string): StreamState {
  return useSyncExternalStore(
    runStore.subscribe,
    () => runStore.getSnapshot()[runId] ?? INITIAL,
  );
}

/**
 * Souscrit au résumé de statuts de tous les runs.
 *
 * Ne redessine que si un statut ou une `pendingQuestion` a changé — pas à
 * chaque `agent_token`.
 */
export function useListeRuns(): RunStatus[] {
  return useSyncExternalStore(
    runStore.subscribe,
    () => runStore.getStatusSnapshot(),
  );
}
