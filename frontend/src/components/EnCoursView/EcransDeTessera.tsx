import type { LigneDeJournal, SalleTessera } from "../../types/salleTessera";
import MoniteurMural, { type LigneDEcran } from "./MoniteurMural";

/** ADR-026 : rouge pour l'échec, ambre pour l'avertissement, zinc sinon. */
const TON_DU_NIVEAU: Record<string, string> = {
  ERROR: "text-red-300",
  CRITICAL: "text-red-300",
  WARNING: "text-amber-300",
};

function heure(ts: string | null): string {
  if (ts === null) return "";
  const t = Date.parse(ts);
  return Number.isNaN(t) ? "" : new Date(t).toLocaleTimeString("fr-FR");
}

function lignesDesRuns(salle: SalleTessera): LigneDEcran[] {
  const lignes: LigneDEcran[] = [];
  for (const run of salle.runs) {
    const ou = [run.ticket_id, run.agent ?? run.etape].filter(Boolean).join(" · ");
    lignes.push({ cle: `${run.project_id}:run`, texte: `${run.project_id} · ${ou}`, ton: "text-blue-300" });
    for (const suivant of run.suivants) {
      lignes.push({ cle: `${run.project_id}:${suivant}`, texte: `puis ${suivant}`, ton: "text-zinc-300" });
    }
  }
  return lignes;
}

function lignesDeLaCi(salle: SalleTessera): LigneDEcran[] {
  return Object.entries(salle.ci_en_attente).flatMap(([projet, tickets]) =>
    tickets.map((t) => ({ cle: `${projet}:${t}`, texte: `${projet} · ${t} · CI ou merge`, ton: "text-amber-300" })),
  );
}

function lignesDuJournal(journal: readonly LigneDeJournal[]): LigneDEcran[] {
  return journal.map((l, i) => ({
    cle: i,
    texte: [heure(l.ts), l.evenement, l.ticket_id ?? l.role].filter(Boolean).join(" "),
    ton: TON_DU_NIVEAU[l.niveau] ?? "text-zinc-300",
  }));
}

/**
 * Les trois moniteurs du mur de la salle Tessera — ticket-726 : les runs vivants et
 * leur file, les PR que le CIWatcher attend, la fin de `tessera.log`. Chaque ligne
 * vient de `GET /tessera/salle` ; sans donnée, l'écran le dit (ADR-058).
 */
export default function EcransDeTessera({ salle }: { salle: SalleTessera }) {
  const file = salle.runs.find((r) => r.file_total > 0);
  const enAttente = Object.values(salle.ci_en_attente).reduce((n, t) => n + t.length, 0);
  const erreurs = salle.journal.some((l) => TON_DU_NIVEAU[l.niveau] === "text-red-300");
  return (
    <div className="mx-auto grid max-w-6xl grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-x-6 gap-y-4">
      <MoniteurMural
        titre="runs en cours"
        statut={file ? <span className="text-blue-300">file {file.file_index} / {file.file_total}</span> : `${salle.runs.length}`}
        lignes={lignesDesRuns(salle)}
        voyant={salle.runs.length > 0 ? "bg-blue-400" : "bg-zinc-600"}
        vide="(aucun run)"
        data={{ "data-ecran-tessera": "runs" }}
      />
      <MoniteurMural
        titre="CIWatcher"
        statut={`${enAttente} PR`}
        lignes={lignesDeLaCi(salle)}
        voyant={enAttente > 0 ? "bg-amber-400" : "bg-zinc-600"}
        vide="(aucune PR en attente)"
        data={{ "data-ecran-tessera": "ci" }}
      />
      <MoniteurMural
        titre="tessera.log"
        statut={erreurs ? <span className="text-red-300">erreur</span> : "ok"}
        lignes={lignesDuJournal(salle.journal)}
        voyant={erreurs ? "bg-red-500" : "bg-blue-400"}
        vide="(journal vide)"
        data={{ "data-ecran-tessera": "journal" }}
      />
    </div>
  );
}
