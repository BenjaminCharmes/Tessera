/**
 * Formatters for durations, dates and costs — ticket-681.
 *
 * One implementation per family. No React here: `design/charts/` and the
 * components all import from this module, and none imports the other way.
 */

const DASH = "—";

/** `run`: « 1m 05s » · `stats`: « 2 min 05 », « 1 h 05 » · `fil`: « 2 min 50 s ». */
export type DurationNotation = "stats" | "fil" | "run";

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

/** A run's length in milliseconds. Null, negative or non-finite gives a dash. */
export function formatDurationMs(ms: number | null, notation: DurationNotation = "stats"): string {
  if (ms === null || !Number.isFinite(ms) || ms < 0) return DASH;
  const s = Math.round(ms / 1000);
  const m = Math.floor(s / 60);
  if (notation === "run") return `${m}m ${pad2(s % 60)}s`;
  if (s < 60) return `${s} s`;
  if (notation === "fil") return `${m} min ${s % 60} s`;
  if (m < 60) return `${m} min ${pad2(s % 60)}`;
  return `${Math.floor(m / 60)} h ${pad2(m % 60)}`;
}

/** Time elapsed since `since` (ISO), or a dash when the instant is unknown. */
export function formatElapsed(since: string | null, now: number): string {
  if (since === null) return DASH;
  const start = Date.parse(since);
  if (Number.isNaN(start)) return DASH;
  const minutes = Math.max(0, Math.floor((now - start) / 60_000));
  if (minutes < 1) return "< 1 min";
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h ${pad2(minutes % 60)}`;
  return `${Math.floor(hours / 24)} j ${hours % 24} h`;
}

/** « 2026-09-28 » → « 28 sept. », without timezone shift: the day is UTC. */
export function formatDay(day: string): string {
  const [y, m, d] = day.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  });
}

/** An ISO instant as « 14/10 07:00 », local time. */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Notation du coût : l'utilisateur ne l'a pas tranchée (ticket-681 — question
// posée, aucune réponse). Les deux notations d'origine sont donc conservées à
// l'identique sous deux noms ; en fixer une seule est un choix d'affichage
// qui lui revient, et se fera en retirant l'une de ces deux fonctions.

/** Cost in the stats notation: « 0.42 $ », cents under one cent. */
export function formatUsd(usd: number): string {
  if (usd < 0 || !Number.isFinite(usd)) return DASH;
  if (usd === 0) return "0 $";
  return usd < 0.01 ? `${(usd * 100).toFixed(2)} ¢` : `${usd.toFixed(usd < 10 ? 2 : 0)} $`;
}

/** Cost in the history notation: « $0.42 », a dash at zero. */
export function formatCout(usd: number): string {
  return usd > 0 ? `$${usd.toFixed(2)}` : DASH;
}
