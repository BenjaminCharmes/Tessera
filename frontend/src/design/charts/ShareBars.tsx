import { SERIES } from "./palette";

/**
 * Une part d'un tout, en barre horizontale — ticket-201.
 *
 * Une seule teinte : les lignes sont des entités comparées sur une même
 * mesure, pas des séries à distinguer. La couleur ne dit rien que la longueur
 * ne dise déjà.
 */
export function ShareBar({ fraction }: { fraction: number }) {
  const pct = Math.min(Math.max(fraction, 0), 1) * 100;
  return (
    <div className="h-1 overflow-hidden rounded-sm bg-zinc-800">
      <div className={`h-full rounded-sm ${SERIES[0].bg}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export interface ShareBarsProps {
  rows: { key: string; value: number; detail?: string }[];
  format: (n: number) => string;
  empty: string;
  /**
   * `share` (défaut) : chaque barre est une part du total, affichée en %.
   * `max` : relative à la plus grande — pour une moyenne, dont la somme ne
   * veut rien dire.
   */
  scale?: "share" | "max";
}

export default function ShareBars({ rows, format, empty, scale = "share" }: ShareBarsProps) {
  const total =
    scale === "share"
      ? rows.reduce((sum, r) => sum + r.value, 0)
      : Math.max(0, ...rows.map((r) => r.value));
  if (rows.length === 0) return <p className="text-xs text-zinc-500">{empty}</p>;
  return (
    <ul className="space-y-2.5">
      {rows.map((r) => {
        const part = total > 0 ? r.value / total : 0;
        return (
          <li key={r.key}>
            <div className="mb-1 flex items-baseline justify-between gap-2 text-xs">
              <span className="truncate font-mono text-zinc-200">{r.key}</span>
              <span className="shrink-0 text-zinc-400">
                {format(r.value)}
                {scale === "share" ? ` · ${(part * 100).toFixed(0)} %` : ""}
                {r.detail ? ` · ${r.detail}` : ""}
              </span>
            </div>
            <ShareBar fraction={part} />
          </li>
        );
      })}
    </ul>
  );
}
