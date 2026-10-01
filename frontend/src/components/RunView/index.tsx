import RegionTitle from "../../design/RegionTitle";
import { BAND } from "../../design/layout";
import PipelineSummary from "../AgentPanel/PipelineSummary";
import { resumeDuCout } from "../../lib/budget";
import FilDuRun from "../FilDuRun";
import type { UseRunActifResult } from "../../hooks/streamState";

/**
 * Ce que le run est en train de faire, au centre de l'écran (ticket-075).
 *
 * Le panneau est un fil chronologique (ticket-222) : Codeur (tour 1) →
 * Sécurité → Reviewer (tour 1) → Validateur → Codeur (tour 2) → …
 * Depuis ticket-257, les entrées sécurité et validateur y figurent aussi,
 * via le composant partagé FilDuRun.
 */
interface RunViewProps {
  stream: UseRunActifResult;
}

export default function RunView({ stream }: RunViewProps) {
  const { entries, currentRound, lastResult, queue } = stream;

  return (
    <div className="flex h-full flex-col bg-zinc-900">
      <div className={`${BAND} justify-between gap-3 border-b border-zinc-700 px-4`}>
        <RegionTitle>Run en cours</RegionTitle>
        <div className="flex items-center gap-3 text-mini text-zinc-400">
          {queue && (
            <span className="text-zinc-300">
              File : {queue.index}/{queue.total}
            </span>
          )}
          {stream.ticketId && (
            <span className="font-mono text-zinc-500">{stream.ticketId}</span>
          )}
          {currentRound > 0 && <span>Tour {currentRound}</span>}
          {(stream.coutUsd > 0 || stream.outils > 0) && (
            <span data-testid="cout-du-run">
              {resumeDuCout(stream.coutUsd, stream.appels, stream.outils)}
            </span>
          )}
          {stream.currentAgent && (
            <span className="text-blue-300">{stream.currentAgent.toUpperCase()}</span>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto py-3">
        {entries.length === 0 && (
          <p className="px-4 text-xs text-zinc-500">
            Le run démarre : la branche se crée et le premier agent se prépare.
          </p>
        )}

        <FilDuRun entries={entries} />

        {lastResult && (
          <PipelineSummary result={lastResult} runClosed={stream.runClosed} />
        )}
      </div>
    </div>
  );
}
