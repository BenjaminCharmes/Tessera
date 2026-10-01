/**
 * Structured logger for the frontend — ticket-251.
 *
 * La convention interdit `console.log` dans les composants, mais aucun outil
 * n'existait pour la respecter : ce module est le seul autorisé à appeler
 * `console` (ESLint `no-console` partout ailleurs). Une ligne JSON par
 * événement — un log qui se lit à l'œil se grep aussi.
 */

type Niveau = "debug" | "info" | "warn" | "error";

type Contexte = Record<string, unknown>;

function emettre(level: Niveau, msg: string, ctx?: Contexte): void {
  const ligne = JSON.stringify({ ts: new Date().toISOString(), level, msg, ...ctx });
  console[level](ligne);
}

export const logger = {
  debug: (msg: string, ctx?: Contexte) => emettre("debug", msg, ctx),
  info: (msg: string, ctx?: Contexte) => emettre("info", msg, ctx),
  warn: (msg: string, ctx?: Contexte) => emettre("warn", msg, ctx),
  error: (msg: string, ctx?: Contexte) => emettre("error", msg, ctx),
};
