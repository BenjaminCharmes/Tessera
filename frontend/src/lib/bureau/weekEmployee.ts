import type { PipelineRun } from "../../types/api";

/** Les runs récents d'un projet, tels que `GET /projects/{id}/runs` les rend. */
export interface ProjectRuns {
  project: string;
  runs: readonly PipelineRun[];
}

/** Le projet distingué : celui qui a le plus de tickets approuvés au premier tour. */
export interface WeekEmployee {
  project: string;
  count: number;
}

const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

/** Approuvé au tour 1, démarré dans les 7 derniers jours : un tour 2 ou un run plus ancien ne compte pas. */
function isFirstTryOfTheWeek(run: PipelineRun, now: number): boolean {
  if (run.approved !== true || run.rounds !== 1) return false;
  const startedAt = Date.parse(run.started_at);
  return !Number.isNaN(startedAt) && startedAt > now - WEEK_MS && startedAt <= now;
}

/** Nombre de tickets distincts approuvés au premier tour sur la semaine. */
export function firstTryCount(runs: readonly PipelineRun[], now: number): number {
  const tickets = new Set(runs.filter((r) => isFirstTryOfTheWeek(r, now)).map((r) => r.ticket_id));
  return tickets.size;
}

/**
 * L'employé de la semaine : le projet au plus grand nombre de tickets approuvés
 * au premier tour. À égalité, le premier de la liste garde la place. `null`
 * quand aucun ticket n'a passé du premier coup : pas de cadre.
 */
export function weekEmployee(all: readonly ProjectRuns[], now: number): WeekEmployee | null {
  let best: WeekEmployee | null = null;
  for (const { project, runs } of all) {
    const count = firstTryCount(runs, now);
    if (count > 0 && (best === null || count > best.count)) best = { project, count };
  }
  return best;
}

/** Le texte de l'infobulle du cadre : « <projet> · codeur, N tickets du 1er coup ». */
export function employeeLabel({ project, count }: WeekEmployee): string {
  return `${project} · codeur, ${count} ticket${count > 1 ? "s" : ""} du 1er coup`;
}
