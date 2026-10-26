import type { ProjetDuBureau } from "../../components/BureauView";
import type { StreamState } from "../../hooks/streamState";
import type { RunActif } from "../../types/api";

export interface ProjetsDuBureau {
  /** Un projet par projet qui a un run, dans l'ordre où leurs runs sont apparus. */
  projets: ProjetDuBureau[];
  /** Les identifiants des projets connus qui n'ont aucun run. */
  auRepos: string[];
}

/** Un tour de chat commite comme un run mais n'a ni poste ni verdict : le pipeline prime. */
function plusPertinent(courant: RunActif | undefined, candidat: RunActif): RunActif {
  if (courant === undefined) return candidat;
  return courant.mode === "chat" && candidat.mode !== "chat" ? candidat : courant;
}

/**
 * Ce que le Bureau dessine : un projet par projet qui a un run, et à part ceux
 * qui n'en ont pas. Le nom est le `project_id`, comme sur la carte de la Liste.
 */
export function projetsDuBureau(
  runs: readonly RunActif[],
  etatDe: (runId: string) => StreamState,
  projetsConnus: readonly string[],
): ProjetsDuBureau {
  const parProjet = new Map<string, RunActif>();
  for (const run of runs) {
    parProjet.set(run.project_id, plusPertinent(parProjet.get(run.project_id), run));
  }
  const projets = [...parProjet].map(([nom, run]) => ({
    nom,
    etat: etatDe(run.run_id),
    runId: run.run_id,
    run,
  }));
  return { projets, auRepos: projetsConnus.filter((id) => !parProjet.has(id)) };
}
