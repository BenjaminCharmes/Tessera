import { formatCount, formatDurationMs, formatUsd } from "../../design/charts/palette";
import { IconBlocked, IconCheck, IconDot } from "../../design/icons";
import type { RecentRun } from "../../types/api";

function Verdict({ run }: { run: RecentRun }) {
  if (run.approved === true)
    return (
      <span className="inline-flex items-center gap-1 text-green-400">
        <IconCheck size={12} /> approuvé
      </span>
    );
  if (run.finished_at === null)
    return (
      <span className="inline-flex items-center gap-1 text-blue-400">
        <IconDot size={8} className="animate-pulse" /> en cours
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 text-red-400">
      <IconBlocked size={12} /> {run.final_status ?? "refusé"}
    </span>
  );
}

function when(iso: string): string {
  return new Date(iso).toLocaleString("fr-FR", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface RecentRunsProps {
  runs: RecentRun[];
  showProject: boolean;
  /** Appelé quand l'utilisateur clique sur une ligne — ouvre la vue du run (ticket-281). */
  onSelect?: (run: RecentRun) => void;
  /** Le message d'une liste vide : une recherche n'est pas une période vide. */
  vide?: string;
}

/** Les derniers runs de la période — ticket-201. */
export default function RecentRuns({
  runs,
  showProject,
  onSelect,
  vide = "Aucun run sur la période.",
}: RecentRunsProps) {
  if (runs.length === 0) {
    return <p className="text-xs text-zinc-500">{vide}</p>;
  }
  const th = "px-2 py-1.5 text-left font-normal text-zinc-500";
  const td = "px-2 py-1.5";
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead className="border-b border-zinc-800 text-mini">
          <tr>
            <th className={th}>Début</th>
            {showProject && <th className={th}>Projet</th>}
            <th className={th}>Ticket</th>
            <th className={`${th} text-right`}>Tokens entrants / sortants</th>
            <th className={`${th} text-right`}>Coût</th>
            <th className={`${th} text-right`}>Durée</th>
            <th className={th}>Issue</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => (
            <tr
              key={r.id}
              onClick={() => onSelect?.(r)}
              className={`border-b border-zinc-800/60 last:border-0 hover:bg-zinc-800/40 ${onSelect ? "cursor-pointer" : ""}`}
            >
              <td className={`${td} whitespace-nowrap text-zinc-400`}>{when(r.started_at)}</td>
              {showProject && <td className={`${td} font-mono text-zinc-300`}>{r.project_id}</td>}
              <td className={`${td} font-mono text-zinc-200`}>{r.ticket_id}</td>
              <td className={`${td} whitespace-nowrap text-right tabular-nums text-zinc-400`}>
                {formatCount(r.input_tokens)} / {formatCount(r.output_tokens)}
              </td>
              <td className={`${td} text-right tabular-nums text-zinc-300`}>{formatUsd(r.cost_usd)}</td>
              <td className={`${td} text-right tabular-nums text-zinc-400`}>
                {formatDurationMs(r.duration_ms)}
              </td>
              <td className={`${td} whitespace-nowrap`}>
                <Verdict run={r} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
