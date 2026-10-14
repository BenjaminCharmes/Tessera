import { useState } from "react";
import type { PipelineRun, Ticket } from "../../types/api";
import {
  classeDuVerdict,
  etatDuRun,
  FILTRES,
  filtrerRuns,
  formatCout,
  formatDate,
  libelleDeLEtat,
  libelleDesTours,
  runsDeTicket,
  triParDate,
} from "./runs";
import StatusPill from "../../design/ui/StatusPill";
import type { FiltreRuns } from "./runs";

interface TousLesRunsProps {
  runs: PipelineRun[];
  tickets: Ticket[];
  /** Opens the detail of the clicked run. */
  onOpen: (runId: string) => void;
}

const COLONNES =
  "grid grid-cols-[110px_minmax(0,1fr)_110px_80px_80px_110px] gap-3 px-3";

/** Every run of the project as a filterable table (ticket-427). */
export default function TousLesRuns({ runs, tickets, onOpen }: TousLesRunsProps) {
  const [filtre, setFiltre] = useState<FiltreRuns>("tous");
  const lignes = filtrerRuns(triParDate(runsDeTicket(runs)), filtre);
  const titres = new Map(tickets.map((t) => [t.id, t.title]));

  return (
    <div className="min-h-0 flex-1 overflow-y-auto p-4">
      <div role="group" aria-label="Filtre des runs" className="mb-3 flex gap-2">
        {FILTRES.map(({ cle, libelle }) => (
          <button
            key={cle}
            type="button"
            aria-pressed={filtre === cle}
            onClick={() => setFiltre(cle)}
            className={`rounded-full px-2.5 py-1 text-xs transition-colors ${
              filtre === cle
                ? "bg-zinc-700 text-zinc-100"
                : "border border-zinc-800 text-zinc-400 hover:text-zinc-200"
            }`}
          >
            {libelle}
          </button>
        ))}
      </div>

      <div className="overflow-hidden rounded-md border border-zinc-800">
        <div
          className={`${COLONNES} bg-zinc-900 py-2 text-mini uppercase tracking-wider text-zinc-500`}
        >
          <span>Ticket</span>
          <span>Titre</span>
          <span>Verdict</span>
          <span>Tours</span>
          <span>Coût</span>
          <span>Date</span>
        </div>
        {lignes.length === 0 && (
          <p className="border-t border-zinc-800 px-3 py-3 text-xs text-zinc-500">
            Aucun run ne correspond à ce filtre.
          </p>
        )}
        {lignes.map((run) => (
          <button
            key={run.id}
            type="button"
            onClick={() => onOpen(run.id)}
            className={`${COLONNES} w-full border-t border-zinc-800 py-2 text-left text-xs text-zinc-200 hover:bg-zinc-800`}
          >
            <span className="truncate font-mono">{run.ticket_id}</span>
            <span className="truncate">{titres.get(run.ticket_id) ?? "—"}</span>
            <span className={classeDuVerdict(run)}>
              {etatDuRun(run) === "interrompu" ? (
                <StatusPill etat="neutre" libelle={libelleDeLEtat("interrompu")} />
              ) : (
                libelleDeLEtat(etatDuRun(run))
              )}
            </span>
            <span className="text-zinc-400">{libelleDesTours(run.rounds)}</span>
            <span className="font-mono text-zinc-400">{formatCout(run.total_cost_usd)}</span>
            <span className="text-zinc-400">{formatDate(run.started_at)}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
