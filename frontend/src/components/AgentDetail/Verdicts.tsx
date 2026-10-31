import { useMemo } from "react";
import { api } from "../../lib/api";
import { useResource } from "../../hooks/useResource";
import { formatDate } from "../../lib/format";
import type { PipelineRun } from "../../types/api";
import {
  classeDuVerdict,
  etatDuRun,
  libelleDeLEtat,
  triParDate,
} from "../HistoriqueView/runs";

const NOMBRE = 5;
const AUCUN: PipelineRun[] = [];

/** « Approuvé après 2 tours » : un refus suivi d'une approbation se voit. */
function libelleDuVerdict(run: PipelineRun): string {
  const libelle = libelleDeLEtat(etatDuRun(run));
  const tours = run.rounds ?? 0;
  return run.approved === true && tours > 1
    ? `${libelle} après ${tours} tours`
    : libelle;
}

/**
 * Les derniers verdicts d'un rôle qui juge — reviewer, validateur, sécurité
 * (ticket-429). Ce sont les issues des derniers runs du projet : le verdict
 * propre à chaque rôle n'est pas encore exposé par l'API.
 */
export default function Verdicts({ projectId }: { projectId: string }) {
  const fetcher = useMemo(
    () => () => api.runs.list(projectId, NOMBRE),
    [projectId],
  );
  const { data, error } = useResource<PipelineRun[]>(fetcher, AUCUN);
  const runs = triParDate(data).slice(0, NOMBRE);

  return (
    <section
      aria-label="Derniers verdicts"
      className="shrink-0 border-t border-zinc-800 px-4 py-3"
    >
      <h3 className="mb-1 text-micro uppercase tracking-wide text-zinc-500">
        Derniers verdicts
      </h3>
      <p className="mb-2 text-micro text-zinc-500">
        Issue des derniers runs du projet.
      </p>
      {error && (
        <p className="text-mini text-red-400">
          Impossible de lire les runs : {error}
        </p>
      )}
      {!error && runs.length === 0 && (
        <p className="text-mini text-zinc-500">Aucun run sur ce projet.</p>
      )}
      <ul className="flex flex-col">
        {runs.map((run) => (
          <li
            key={run.id}
            className="grid grid-cols-[7rem_minmax(0,1fr)_auto] gap-3 border-b border-zinc-800 py-1 text-mini last:border-b-0"
          >
            <span className="font-mono text-zinc-200">{run.ticket_id}</span>
            <span className="text-zinc-500">{formatDate(run.started_at)}</span>
            <span className={classeDuVerdict(run)}>{libelleDuVerdict(run)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
