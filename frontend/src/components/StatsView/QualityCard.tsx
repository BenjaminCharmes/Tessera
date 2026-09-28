import { formatDurationMs } from "../../design/charts/palette";
import type { RunQuality } from "../../types/api";

/**
 * L'issue d'un run est un **état** : elle prend les couleurs d'ADR-026, pas
 * celles des séries. Chaque segment porte aussi son nom, jamais la couleur seule.
 */
const STATUS_COLOR: Record<string, string> = {
  done: "bg-green-500",
  blocked: "bg-red-500",
  "in-review": "bg-amber-500",
};

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-micro text-zinc-500">{label}</p>
      <p className="text-sm font-semibold tabular-nums text-zinc-100">{value}</p>
    </div>
  );
}

export default function QualityCard({ quality }: { quality: RunQuality }) {
  if (quality.finished_runs === 0) {
    return <p className="text-xs text-zinc-500">Aucun run terminé sur la période.</p>;
  }
  const total = quality.by_status.reduce((sum, s) => sum + s.count, 0);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <Figure
          label="Approuvés"
          value={quality.approval_rate === null ? "—" : `${Math.round(quality.approval_rate * 100)} %`}
        />
        <Figure
          label="Tours moyens"
          value={quality.avg_rounds === null ? "—" : quality.avg_rounds.toFixed(1)}
        />
        <Figure label="Durée moyenne" value={formatDurationMs(quality.avg_run_duration_ms)} />
      </div>
      <div className="flex h-2 gap-0.5 overflow-hidden rounded-sm">
        {quality.by_status.map((s) => (
          <div
            key={s.status}
            className={STATUS_COLOR[s.status] ?? "bg-zinc-600"}
            style={{ width: `${(s.count / total) * 100}%` }}
            title={`${s.status} · ${s.count}`}
          />
        ))}
      </div>
      <ul className="space-y-1 text-xs">
        {quality.by_status.map((s) => (
          <li key={s.status} className="flex items-center gap-2">
            <span
              className={`h-2 w-2 shrink-0 rounded-full ${STATUS_COLOR[s.status] ?? "bg-zinc-600"}`}
              aria-hidden="true"
            />
            <span className="flex-1 font-mono text-zinc-200">{s.status}</span>
            <span className="text-zinc-400">
              {s.count} · {((s.count / total) * 100).toFixed(0)} %
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
