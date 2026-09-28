import { useState } from "react";
import { DataTable, EmptyChart, Grid, Tooltip, XLabels } from "./frame";
import { niceMax, SERIES } from "./palette";

export interface LineSeries {
  name: string;
  values: number[];
}

export interface TimeLinesProps {
  labels: string[];
  /** Au plus trois, sur **une** échelle : deux mesures d'unités différentes font deux graphiques. */
  series: LineSeries[];
  format: (n: number) => string;
  empty: string;
}

/**
 * Plusieurs séries par jour, en courbes — ticket-201.
 *
 * Le tracé est un SVG étiré sur la largeur ; `non-scaling-stroke` garde le
 * trait à 2 px. Les points et le réticule sont en HTML, pour rester ronds.
 */
export default function TimeLines({ labels, series, format, empty }: TimeLinesProps) {
  const [hover, setHover] = useState<number | null>(null);
  const top = Math.max(0, ...series.flatMap((s) => s.values));
  if (top === 0) return <EmptyChart>{empty}</EmptyChart>;
  const max = niceMax(top);
  const n = labels.length;
  const x = (i: number) => ((i + 0.5) / n) * 100;
  const y = (v: number) => 100 - (v / max) * 100;
  const shown = series.slice(0, SERIES.length);

  return (
    <div>
      <ul className="mb-3 flex flex-wrap gap-4 text-mini text-zinc-400">
        {shown.map((s, k) => (
          <li key={s.name} className="flex items-center gap-1.5">
            <span className={`h-0.5 w-3 rounded ${SERIES[k].bg}`} aria-hidden="true" />
            {s.name}
          </li>
        ))}
      </ul>
      <div className="pl-12">
        <div className="relative h-40" onMouseLeave={() => setHover(null)}>
          <Grid max={max} format={format} />
          <svg
            className="absolute inset-0 h-full w-full overflow-visible"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            {shown.map((s, k) => (
              <polyline
                key={s.name}
                data-testid="line"
                className={SERIES[k].stroke}
                fill="none"
                strokeWidth={2}
                strokeLinejoin="round"
                vectorEffect="non-scaling-stroke"
                points={s.values.map((v, i) => `${x(i)},${y(v)}`).join(" ")}
              />
            ))}
          </svg>
          {hover !== null && (
            <>
              <div
                className="pointer-events-none absolute inset-y-0 border-l border-zinc-600"
                style={{ left: `${x(hover)}%` }}
              />
              {shown.map((s, k) => (
                <span
                  key={s.name}
                  className={`pointer-events-none absolute h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-zinc-900 ${SERIES[k].bg}`}
                  style={{ left: `${x(hover)}%`, top: `${y(s.values[hover])}%` }}
                />
              ))}
              <Tooltip x={x(hover) / 100}>
                <div className="text-zinc-400">{labels[hover]}</div>
                {shown.map((s, k) => (
                  <div key={s.name} className="flex items-center gap-1.5">
                    <span className={`h-2 w-2 rounded-full ${SERIES[k].bg}`} aria-hidden="true" />
                    {s.name} · {format(s.values[hover])}
                  </div>
                ))}
              </Tooltip>
            </>
          )}
          <div className="absolute inset-0 flex">
            {labels.map((l, i) => (
              <div key={l} className="h-full flex-1" onMouseEnter={() => setHover(i)} />
            ))}
          </div>
        </div>
        <XLabels labels={labels} />
      </div>
      <DataTable
        caption={shown.map((s) => s.name).join(", ")}
        headers={["Jour", ...shown.map((s) => s.name)]}
        rows={labels.map((l, i) => [l, ...shown.map((s) => format(s.values[i]))])}
      />
    </div>
  );
}
