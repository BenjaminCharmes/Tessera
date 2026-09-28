/**
 * Les couleurs des séries — ticket-201, ADR-047.
 *
 * Trois teintes dans un ordre fixe : une série garde sa couleur quel que soit
 * son rang, et une quatrième ne s'invente pas — elle rejoint « autres », en
 * zinc. Au-delà de trois, la séparation daltonienne ne tient plus.
 *
 * Les classes sont écrites en entier : Tailwind ne génère que ce qu'il lit.
 */
export const SERIES = [
  { fill: "fill-data-1", stroke: "stroke-data-1", bg: "bg-data-1" },
  { fill: "fill-data-2", stroke: "stroke-data-2", bg: "bg-data-2" },
  { fill: "fill-data-3", stroke: "stroke-data-3", bg: "bg-data-3" },
] as const;

/** Ce qui ne tient pas dans les trois teintes : neutre, donc zinc. */
export const OTHER = { fill: "fill-zinc-600", stroke: "stroke-zinc-600", bg: "bg-zinc-600" };

export type SeriesColor = (typeof SERIES)[number] | typeof OTHER;

export interface Part {
  key: string;
  value: number;
  color: SeriesColor;
}

/** Les trois plus grosses parts, puis « autres » : une quatrième teinte ne s'invente pas. */
export function foldSlices(slices: { key: string; value: number }[]): Part[] {
  const sorted = [...slices].filter((s) => s.value > 0).sort((a, b) => b.value - a.value);
  const head = sorted.slice(0, SERIES.length).map((s, i) => ({ ...s, color: SERIES[i] }));
  const rest = sorted.slice(SERIES.length).reduce((sum, s) => sum + s.value, 0);
  return rest > 0 ? [...head, { key: "autres", value: rest, color: OTHER }] : head;
}

/** Arrondit un maximum vers le haut à 1, 2 ou 5 × 10ⁿ, pour un axe lisible. */
export function niceMax(value: number): number {
  if (value <= 0) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const step = [1, 2, 5, 10].find((m) => m * magnitude >= value) ?? 10;
  return step * magnitude;
}

export function formatUsd(usd: number): string {
  if (usd === 0) return "0 $";
  return usd < 0.01 ? `${(usd * 100).toFixed(2)} ¢` : `${usd.toFixed(usd < 10 ? 2 : 0)} $`;
}

export function formatCount(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)} M`;
  if (n >= 10_000) return `${Math.round(n / 1000)} k`;
  return n.toLocaleString("fr-FR");
}

export function formatDurationMs(ms: number | null): string {
  if (ms === null) return "—";
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s} s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} min ${String(s % 60).padStart(2, "0")}`;
  return `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")}`;
}

/** « 2026-09-28 » → « 28 sept. », sans décalage de fuseau : le jour est UTC. */
export function formatDay(day: string): string {
  const [y, m, d] = day.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  });
}
