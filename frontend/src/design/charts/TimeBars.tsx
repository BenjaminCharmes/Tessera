import { useState } from "react";
import { DataTable, EmptyChart, Grid, Tooltip, XLabels } from "./frame";
import { niceMax, SERIES } from "./palette";

export interface TimeBarsProps {
  /** Le nom de la mesure : titre de la vue tableau et de l'infobulle. */
  label: string;
  points: { label: string; value: number }[];
  format: (n: number) => string;
  empty: string;
}

/**
 * Une mesure par jour, en barres — ticket-201.
 *
 * Une seule série, donc pas de légende : le titre de la carte la nomme. Les
 * barres partent de la ligne de base, arrondies au sommet seulement.
 */
export default function TimeBars({ label, points, format, empty }: TimeBarsProps) {
  const [hover, setHover] = useState<number | null>(null);
  const top = Math.max(0, ...points.map((p) => p.value));
  if (top === 0) return <EmptyChart>{empty}</EmptyChart>;
  const max = niceMax(top);
  const n = points.length;

  return (
    <div className="pl-12">
      <div className="relative h-40" onMouseLeave={() => setHover(null)}>
        <Grid max={max} format={format} />
        <div className="absolute inset-0 flex items-end gap-px">
          {points.map((p, i) => (
            <div
              key={p.label}
              data-testid="bar"
              className="flex h-full flex-1 items-end"
              onMouseEnter={() => setHover(i)}
            >
              <div
                className={`w-full rounded-t-sm ${SERIES[0].bg} ${
                  hover !== null && hover !== i ? "opacity-50" : ""
                }`}
                style={{ height: `${(p.value / max) * 100}%` }}
              />
            </div>
          ))}
        </div>
        {hover !== null && (
          <Tooltip x={(hover + 0.5) / n}>
            <span className="text-zinc-400">{points[hover].label}</span>
            {" · "}
            {format(points[hover].value)}
          </Tooltip>
        )}
      </div>
      <XLabels labels={points.map((p) => p.label)} />
      <DataTable
        caption={label}
        headers={["Jour", label]}
        rows={points.map((p) => [p.label, format(p.value)])}
      />
    </div>
  );
}
