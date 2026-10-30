import type { RecentRun } from "../../types/api";
import type { LigneDeJournal, SalleTessera } from "../../types/salleTessera";
import type { LigneDEcran } from "./MoniteurMural";

/** Un écran de la salle Tessera, que l'on déplie sous la salle — ticket-726. */
export type EcranDeTessera = "runs" | "ci" | "journal" | "derniers";
/** Les lignes qu'un moniteur du mur montre ; le panneau déplié les donne toutes. */
export const LIGNES_AU_MUR = 4;
/** Le run en cours, puis ses suivants, tiennent sur un moniteur. */
const SUIVANTS_AU_MUR = LIGNES_AU_MUR - 1;

/** ADR-026 : rouge pour l'échec, ambre pour l'avertissement, zinc sinon. */
export const TON_DU_NIVEAU: Record<string, string> = {
  ERROR: "text-red-300",
  CRITICAL: "text-red-300",
  WARNING: "text-amber-300",
};

function heure(ts: string | null): string {
  if (ts === null) return "";
  const t = Date.parse(ts);
  return Number.isNaN(t) ? "" : new Date(t).toLocaleTimeString("fr-FR");
}

export function lignesDesRuns(salle: SalleTessera, suivants = SUIVANTS_AU_MUR): LigneDEcran[] {
  const lignes: LigneDEcran[] = [];
  for (const run of salle.runs) {
    const ou = [run.ticket_id, run.agent ?? run.etape].filter(Boolean).join(" · ");
    lignes.push({ cle: `${run.project_id}:run`, texte: `${run.project_id} · ${ou}`, ton: "text-blue-300" });
    for (const suivant of run.suivants.slice(0, suivants)) {
      lignes.push({ cle: `${run.project_id}:${suivant}`, texte: `puis ${suivant}`, ton: "text-zinc-300" });
    }
  }
  return lignes;
}

export function lignesDeLaCi(salle: SalleTessera): LigneDEcran[] {
  return Object.entries(salle.ci_en_attente).flatMap(([projet, tickets]) =>
    tickets.map((t) => ({ cle: `${projet}:${t}`, texte: `${projet} · ${t} · CI ou merge`, ton: "text-amber-300" })),
  );
}

export function lignesDuJournal(journal: readonly LigneDeJournal[]): LigneDEcran[] {
  return journal.map((l, i) => ({
    cle: i,
    texte: [heure(l.ts), l.evenement, l.ticket_id ?? l.role].filter(Boolean).join(" "),
    ton: TON_DU_NIVEAU[l.niveau] ?? "text-zinc-300",
  }));
}

/** ADR-026 : vert pour l'approuvé, rouge pour le refusé, zinc tant qu'il n'y a pas de verdict. */
function verdict(run: RecentRun): { mot: string; ton: string } {
  if (run.approved === true) return { mot: "approuvé", ton: "text-green-300" };
  if (run.approved === false) return { mot: "refusé", ton: "text-red-300" };
  return { mot: run.finished_at === null ? "en cours" : "sans verdict", ton: "text-zinc-300" };
}

/** Les derniers runs du pipeline, tous projets : verdict, coût et durée (ticket-726). */
export function lignesDesDerniers(runs: readonly RecentRun[]): LigneDEcran[] {
  return runs.map((run) => {
    const { mot, ton } = verdict(run);
    const minutes = run.duration_ms === null ? null : Math.max(1, Math.round(run.duration_ms / 60_000));
    const cout = `${run.cost_usd.toFixed(2).replace(".", ",")} $`;
    return {
      cle: run.id,
      texte: [run.project_id, run.ticket_id, mot, cout, minutes === null ? null : `${minutes} min`].filter(Boolean).join(" · "),
      ton,
    };
  });
}
