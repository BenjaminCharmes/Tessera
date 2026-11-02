import type { SidebarPanel } from "../../components/Sidebar/panels";
import type { VueCentre } from "../../vueDuCentre";
import type { OrchestratorEvent, RunActif } from "../../types/api";
import type { StreamState } from "../streamState";

/**
 * Returns the panel to activate when the user selects a project, from a card,
 * the selector or the list. The current panel always stays: the user was
 * already where they wanted to be, and chaining several projects must not
 * send them back to the tickets each time (ticket-271, ticket-425).
 *
 * Kept as a named function so an exception can be added in one place.
 */
export function panelAfterProjectSwitch(
  current: SidebarPanel,
): SidebarPanel {
  return current;
}

/**
 * Returns the effective statistics scope — ticket-258.
 *
 * When no project is active there is nothing to scope to: the effective scope
 * is always "tous", regardless of the user's prior selection.  When a project
 * is active the user's explicit choice is honoured.
 */
export function porteeEffectiveFor(
  project: { id: string } | null,
  statsPortee: "projet" | "tous",
): "projet" | "tous" {
  return project === null ? "tous" : statsPortee;
}

/**
 * Indique si « Revenir au run en cours » doit être proposé — ticket-283.
 *
 * Avant ticket-283, le calcul était `runEnCours && !runAuPremierPlan`. Ouvrir
 * un fichier ou un diff ne remettait pas `runAuPremierPlan` à faux : le bouton
 * restait caché alors qu'un run tournait derrière l'éditeur ou le diff.
 */
export function runCachePour(runEnCours: boolean, vueCentre: VueCentre): boolean {
  return runEnCours && vueCentre !== "run";
}

/**
 * Next `showKanban` value after the user clicks the board toggle — ticket-287.
 *
 * The decision is based on the currently *displayed* view, not on the raw
 * `showKanban` flag.  When the board is showing, the toggle returns to the
 * editor; from any other view (run, editor, diff) it opens the board.
 *
 * This avoids the situation where `showKanban` is already `true` while the
 * run occupies the foreground: a first click would have flipped it to `false`
 * and shown the editor instead of the board.
 */
export function prochainEtatKanban(vueCentre: VueCentre): boolean {
  return vueCentre !== "kanban";
}

/**
 * Événements à afficher dans le Pipeline log — ticket-283.
 *
 * Quand l'utilisateur a sélectionné un run dans la Supervision, c'est celui-là
 * qu'on affiche — sinon les événements du projet actif.
 */
export function eventsAffichiesFor(
  selection: string | null,
  runs: RunActif[],
  etatDe: (runId: string) => StreamState,
  streamEvents: OrchestratorEvent[],
): OrchestratorEvent[] {
  const run = selection ? (runs.find((r) => r.run_id === selection) ?? null) : null;
  return run ? etatDe(run.run_id).events : streamEvents;
}
