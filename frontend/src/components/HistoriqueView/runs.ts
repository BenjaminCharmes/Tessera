import type { EtatPastille } from "../../design/ui/StatusPill";
import { formatDurationMs } from "../../lib/format";
import type { PipelineRun } from "../../types/api";

/** Where a run stands, from the point of view of the History tab. */
export type EtatDuRun = "approuve" | "refuse" | "bloque" | "en-cours" | "interrompu";

/** Cause écrite par le backend sur un run que le processus a laissé derrière lui. */
const CAUSE_REDEMARRAGE = "backend restarted";

export type FiltreRuns = "tous" | "approuves" | "refuses" | "tours";

export const FILTRES: { cle: FiltreRuns; libelle: string }[] = [
  { cle: "tous", libelle: "Tous" },
  { cle: "approuves", libelle: "Approuvés" },
  { cle: "refuses", libelle: "Refusés ou bloqués" },
  { cle: "tours", libelle: "Plusieurs tours" },
];

/**
 * Interrupted: closed without a single finished round, by a restart rather
 * than by a cause of its own (veille, redémarrage du backend).
 */
export function estInterrompu(run: PipelineRun): boolean {
  if (run.finished_at === null || run.final_status !== "blocked") return false;
  if ((run.rounds ?? 0) > 0) return false;
  return !run.arret || run.arret.startsWith(CAUSE_REDEMARRAGE);
}

/**
 * Classifies a run: approved, refused, blocked (stopped on the way),
 * interrupted or running.
 */
export function etatDuRun(run: PipelineRun): EtatDuRun {
  if (run.approved === true) return "approuve";
  if (run.finished_at === null && run.final_status === null) return "en-cours";
  if (estInterrompu(run)) return "interrompu";
  return run.final_status === "blocked" ? "bloque" : "refuse";
}

/**
 * Keeps one row per ticket run: a queue's parent run is dropped as soon as a
 * child points to it. A run with neither parent nor child stays.
 */
export function runsDeTicket(runs: readonly PipelineRun[]): PipelineRun[] {
  const parents = new Set<string>();
  for (const run of runs) {
    if (run.parent_run_id) parents.add(run.parent_run_id);
  }
  return runs.filter((run) => !parents.has(run.id));
}

export function libelleDeLEtat(etat: EtatDuRun): string {
  switch (etat) {
    case "interrompu":
      return "Interrompu";
    case "approuve":
      return "Approuvé";
    case "refuse":
      return "Refusé";
    case "bloque":
      return "Bloqué";
    case "en-cours":
      return "En cours";
  }
}

/** Text colour of a verdict — ADR-026: green, amber, red and blue only. */
export function classeDuVerdict(run: PipelineRun): string {
  const etat = etatDuRun(run);
  if (etat === "en-cours") return "text-blue-400";
  if (etat === "interrompu") return "text-zinc-400";
  if (etat !== "approuve") return "text-red-400";
  return (run.rounds ?? 0) > 1 ? "text-amber-400" : "text-green-400";
}

/**
 * The pill state of a verdict, per the charter: approved is green (amber when
 * it took several rounds), running is blue, anything else is red.
 */
export function pastilleDuRun(run: PipelineRun): EtatPastille {
  const etat = etatDuRun(run);
  if (etat === "en-cours") return "en-cours";
  // Un run interrompu (veille, redémarrage) n'a pas échoué : neutre (ticket-443).
  if (etat === "interrompu") return "neutre";
  if (etat !== "approuve") return "echec";
  return (run.rounds ?? 0) > 1 ? "attention" : "reussi";
}

export function libelleDesTours(rounds: number | null): string {
  if (rounds === null) return "—";
  return `${rounds} tour${rounds > 1 ? "s" : ""}`;
}

/** Newest run first; the API order is not relied on. */
export function triParDate(runs: readonly PipelineRun[]): PipelineRun[] {
  return [...runs].sort(
    (a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime(),
  );
}

export function filtrerRuns(
  runs: readonly PipelineRun[],
  filtre: FiltreRuns,
): PipelineRun[] {
  switch (filtre) {
    case "tous":
      return [...runs];
    case "approuves":
      return runs.filter((r) => etatDuRun(r) === "approuve");
    case "refuses": {
      return runs.filter((r) => {
        const etat = etatDuRun(r);
        return etat === "refuse" || etat === "bloque" || etat === "interrompu";
      });
    }
    case "tours":
      return runs.filter((r) => (r.rounds ?? 0) > 1);
  }
}

/** The run to show: the selected one, else the most recent, else null. */
export function runAffiche(
  runs: readonly PipelineRun[],
  selectionne: string | null,
): PipelineRun | null {
  const choisi = runs.find((r) => r.id === selectionne);
  return choisi ?? triParDate(runs)[0] ?? null;
}

export function formatDuree(run: PipelineRun): string {
  if (run.finished_at === null) return "En cours…";
  // Un run interrompu est resté ouvert des heures : sa durée ne dit rien.
  if (estInterrompu(run)) return "—";
  const ms = new Date(run.finished_at).getTime() - new Date(run.started_at).getTime();
  return formatDurationMs(ms, "run");
}

/**
 * Pull request URL for a GitHub remote (`owner/repo` or a github.com URL).
 * Any other host gets no link: the URL scheme is not known.
 */
export function lienPr(remote: string | null, numero: number | null): string | null {
  if (remote === null || numero === null) return null;
  const nu = remote.replace(/\.git$/, "").replace(/\/$/, "");
  const correspondance =
    /^(?:https:\/\/github\.com\/)?([\w.-]+\/[\w.-]+)$/.exec(nu);
  return correspondance ? `https://github.com/${correspondance[1]}/pull/${numero}` : null;
}
