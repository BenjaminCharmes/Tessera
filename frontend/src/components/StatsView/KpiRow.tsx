import { formatCount, formatDurationMs, formatUsd } from "../../design/charts/palette";
import type { RunQuality, UsageTotals } from "../../types/api";

function Tile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="min-w-0 rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-3">
      <p className="truncate text-mini text-zinc-500">{label}</p>
      <p className="mt-1 text-xl font-semibold tabular-nums text-zinc-100">{value}</p>
      {sub && <p className="mt-0.5 truncate text-micro text-zinc-500">{sub}</p>}
    </div>
  );
}

/** Les chiffres de tête de la période — ticket-201. */
export default function KpiRow({ totals, quality }: { totals: UsageTotals; quality: RunQuality }) {
  const rate = quality.approval_rate;
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      <Tile label="Runs" value={formatCount(totals.runs)} sub={`${totals.calls} appels d'agent`} />
      <Tile
        label="Tokens entrants"
        value={formatCount(totals.input_tokens)}
        sub={`${formatCount(totals.cache_read_tokens)} lus en cache`}
      />
      <Tile label="Tokens sortants" value={formatCount(totals.output_tokens)} />
      <Tile
        label="Coût total"
        value={formatUsd(totals.cost_usd)}
        sub={`dont chat ${formatUsd(totals.chat_cost_usd)}`}
      />
      <Tile
        label="Temps d'agent"
        value={formatDurationMs(totals.call_duration_ms)}
        sub="cumul des appels"
      />
      <Tile
        label="Taux d'approbation"
        value={rate === null ? "—" : `${Math.round(rate * 100)} %`}
        sub={`${quality.finished_runs} run${quality.finished_runs > 1 ? "s" : ""} terminé${quality.finished_runs > 1 ? "s" : ""}`}
      />
    </div>
  );
}
