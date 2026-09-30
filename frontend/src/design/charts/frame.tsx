import type { ReactNode } from "react";

/**
 * Le mobilier commun aux séries temporelles — ticket-201 : grille, bornes de
 * l'axe, infobulle. Récessif par construction : zinc, trait fin, trois lignes.
 */
export function Grid({ max, format }: { max: number; format: (n: number) => string }) {
  return (
    <div className="pointer-events-none absolute inset-0" aria-hidden="true">
      {[1, 0.5, 0].map((f) => (
        <div
          key={f}
          className="absolute inset-x-0 border-t border-zinc-800"
          style={{ top: `${(1 - f) * 100}%` }}
        >
          <span className="absolute -top-2 right-full mr-2 whitespace-nowrap text-micro text-zinc-500">
            {format(max * f)}
          </span>
        </div>
      ))}
    </div>
  );
}

/** Première, médiane et dernière étiquette : assez pour situer, jamais serré. */
export function XLabels({ labels }: { labels: string[] }) {
  if (labels.length === 0) return null;
  const mid = Math.floor((labels.length - 1) / 2);
  const picks = labels.length > 2 ? [0, mid, labels.length - 1] : labels.map((_, i) => i);
  return (
    <div className="relative mt-1 h-4 text-micro text-zinc-500" aria-hidden="true">
      {picks.map((i) => (
        <span
          key={i}
          className="absolute -translate-x-1/2 whitespace-nowrap"
          style={{ left: `${((i + 0.5) / labels.length) * 100}%` }}
        >
          {labels[i]}
        </span>
      ))}
    </div>
  );
}

/** Une infobulle ancrée à une fraction de la largeur, au-dessus du tracé. */
export function Tooltip({ x, children }: { x: number; children: ReactNode }) {
  const align = x < 0.2 ? "translate-x-0" : x > 0.8 ? "-translate-x-full" : "-translate-x-1/2";
  return (
    <div
      role="tooltip"
      className={`pointer-events-none absolute -top-2 z-10 -translate-y-full ${align} whitespace-nowrap rounded border border-zinc-700 bg-zinc-950 px-2 py-1 text-mini text-zinc-200 shadow-lg`}
      style={{ left: `${x * 100}%` }}
    >
      {children}
    </div>
  );
}

/** La vue tableau des données : lue par un lecteur d'écran, invisible sinon. */
export function DataTable({
  caption,
  headers,
  rows,
}: {
  caption: string;
  headers: string[];
  rows: string[][];
}) {
  // `sr-only` est posé sur le <div>, pas sur le <table> : un tableau ignore
  // `height: 1px` et `overflow: hidden` (il grandit pour contenir ses lignes),
  // alors qu'un bloc les respecte. Sans ancêtre positionné, le div absolu
  // échappe au conteneur qui défile et allonge la page ; le wrapper `relative`
  // l'y retient.
  return (
    <div className="relative" data-testid="data-table">
      <div className="sr-only">
        <table>
          <caption>{caption}</caption>
          <thead>
            <tr>
              {headers.map((h) => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r[0]}>
                {r.map((c, i) => (
                  <td key={i}>{c}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function EmptyChart({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-40 items-center justify-center rounded border border-dashed border-zinc-800 text-xs text-zinc-500">
      {children}
    </div>
  );
}
