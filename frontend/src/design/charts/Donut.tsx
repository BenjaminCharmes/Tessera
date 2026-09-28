import { useState } from "react";
import { EmptyChart } from "./frame";
import { foldSlices } from "./palette";

export interface DonutProps {
  slices: { key: string; value: number }[];
  format: (n: number) => string;
  /** Ce que dit le centre de l'anneau sous le total. */
  caption: string;
  empty: string;
}

const R = 42;
const CIRCUMFERENCE = 2 * Math.PI * R;
/** L'écart entre deux parts, en unités de circonférence : l'équivalent de 2 px. */
const GAP = 1.5;

/**
 * Une part du tout — ticket-201. Réservé aux ventilations à peu de parts :
 * la légende porte les valeurs exactes, l'anneau ne donne que la forme.
 */
export default function Donut({ slices, format, caption, empty }: DonutProps) {
  const [hover, setHover] = useState<string | null>(null);
  const parts = foldSlices(slices);
  const total = parts.reduce((sum, p) => sum + p.value, 0);
  if (total === 0) return <EmptyChart>{empty}</EmptyChart>;

  const arcs = parts.map((p, i) => ({
    ...p,
    length: (p.value / total) * CIRCUMFERENCE,
    offset: (parts.slice(0, i).reduce((sum, q) => sum + q.value, 0) / total) * CIRCUMFERENCE,
  }));
  const focus = parts.find((p) => p.key === hover);

  return (
    <div className="flex flex-wrap items-center justify-center gap-5">
      <div className="relative h-32 w-32 shrink-0">
        <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90" aria-hidden="true">
          <circle cx="50" cy="50" r={R} fill="none" strokeWidth="10" className="stroke-zinc-800" />
          {arcs.map((a) => (
            <circle
              key={a.key}
              data-testid="slice"
              cx="50"
              cy="50"
              r={R}
              fill="none"
              strokeWidth={hover === a.key ? 12 : 10}
              className={`${a.color.stroke} transition-[stroke-width]`}
              strokeDasharray={`${Math.max(a.length - (arcs.length > 1 ? GAP : 0), 0.5)} ${CIRCUMFERENCE}`}
              strokeDashoffset={-a.offset}
              onMouseEnter={() => setHover(a.key)}
              onMouseLeave={() => setHover(null)}
            />
          ))}
        </svg>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-sm font-semibold text-zinc-100">
            {format(focus ? focus.value : total)}
          </span>
          <span className="max-w-20 truncate text-micro text-zinc-500">
            {focus ? focus.key : caption}
          </span>
        </div>
      </div>
      <ul className="min-w-44 flex-1 space-y-1.5">
        {parts.map((p) => (
          <li
            key={p.key}
            className={`flex items-center gap-2 text-xs ${hover && hover !== p.key ? "opacity-50" : ""}`}
            onMouseEnter={() => setHover(p.key)}
            onMouseLeave={() => setHover(null)}
          >
            <span className={`h-2 w-2 shrink-0 rounded-full ${p.color.bg}`} aria-hidden="true" />
            <span className="min-w-0 flex-1 truncate font-mono text-zinc-200">{p.key}</span>
            <span className="shrink-0 text-zinc-400">
              {format(p.value)} · {((p.value / total) * 100).toFixed(0)} %
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
