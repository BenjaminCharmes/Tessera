import { useMemo } from "react";
import { api } from "../lib/api";
import { weekEmployee } from "../lib/bureau/weekEmployee";
import type { ProjectRuns, WeekEmployee } from "../lib/bureau/weekEmployee";
import { useResource } from "./useResource";

/** `GET /projects/{id}/runs` plafonne à 100 : de quoi couvrir une semaine de tickets. */
const RUNS_PER_PROJECT = 100;
const NONE: readonly ProjectRuns[] = [];
const SEPARATOR = "\u0000";

/** Les runs d'un projet ; un projet qui ne répond pas ne compte pas, il n'efface pas les autres. */
function readRuns(project: string): Promise<ProjectRuns> {
  return api.runs
    .list(project, RUNS_PER_PROJECT)
    .then((runs) => ({ project, runs }))
    .catch(() => ({ project, runs: [] }));
}

/**
 * L'employé de la semaine (ticket-602) : le projet qui a le plus de tickets
 * approuvés au premier tour sur les 7 derniers jours. Les runs se relisent à
 * chaque changement de la liste des projets et à chaque run clos
 * (`signalRunsClos`) ; la fenêtre de 7 jours, elle, se mesure à `now` — l'horloge
 * unique de la vue, aucun minuteur de plus.
 */
export function useWeekEmployee(
  projects: readonly string[],
  now: number,
  signalRunsClos: number,
): WeekEmployee | null {
  // Triée : l'ordre des runs vivants ne relance pas la lecture, et l'égalité se tranche par le nom.
  const key = [...projects].sort().join(SEPARATOR);
  const fetcher = useMemo(
    () => (key === "" ? null : () => Promise.all(key.split(SEPARATOR).map(readRuns))),
    // `signalRunsClos` ne sert pas dans le fetcher : changer l'identité de celui-ci est
    // le moyen de relire (voir `useResource`), comme `useRestants`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [key, signalRunsClos],
  );
  const { data } = useResource<readonly ProjectRuns[]>(fetcher, NONE);
  return useMemo(() => weekEmployee(data, now), [data, now]);
}
