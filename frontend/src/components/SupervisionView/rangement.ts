import type { StreamState } from "../../hooks/streamState";
import type { RunActif } from "../../types/api";
import type { EntreeMenuFermer } from "./MenuFermer";
import { issueDuRun } from "./issueDuRun";
import type { IssueDuRun } from "./issueDuRun";

type EtatDe = (runId: string) => StreamState;

/** Les runs déjà clos : ceux qu'on peut ranger. */
export function runsClosDe(runs: readonly RunActif[], etatDe: EtatDe): RunActif[] {
  return runs.filter((r) => etatDe(r.run_id).runClosed);
}

/** Les identifiants à ranger pour une issue, ou pour tous les runs clos quand `issue` est `null`. */
export function idsARanger(
  runs: readonly RunActif[],
  etatDe: EtatDe,
  issue: IssueDuRun | null,
): string[] {
  return runsClosDe(runs, etatDe)
    .filter((r) => issue === null || issueDuRun(etatDe(r.run_id)) === issue)
    .map((r) => r.run_id);
}

/** Les entrées du menu « Fermer par lot », avec le compte de chaque issue. */
export function entreesDuMenu(runs: readonly RunActif[], etatDe: EtatDe): EntreeMenuFermer[] {
  const compter = (issue: IssueDuRun | null) => idsARanger(runs, etatDe, issue).length;
  return [
    { label: "Les terminés", issue: "termine", count: compter("termine") },
    { label: "Les bloqués", issue: "bloque", count: compter("bloque") },
    { label: "En erreur", issue: "erreur", count: compter("erreur") },
    { label: "Tous les runs clos", issue: null, count: compter(null) },
  ];
}
