import { useState } from "react";
import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import type { PipelineRun, Project, Ticket } from "../../types/api";
import DetailDuRun from "./DetailDuRun";
import TousLesRuns from "./TousLesRuns";
import { runAffiche } from "./runs";

/** What the History tab needs from the cockpit (ticket-427). */
export interface HistoriqueProps {
  runs: PipelineRun[];
  loading: boolean;
  error: string | null;
  /** Identifiant du run choisi dans la colonne, null tant qu'aucun ne l'est. */
  runSelectionne: string | null;
  onSelectRun: (runId: string) => void;
  /** Tous les tickets du projet, pour retrouver le titre d'un run. */
  tickets: Ticket[];
}

interface HistoriqueViewProps extends HistoriqueProps {
  project: Project | null;
}

type Vue = "detail" | "tous";

const VUES: { cle: Vue; libelle: string }[] = [
  { cle: "detail", libelle: "Détail du run" },
  { cle: "tous", libelle: "Tous les runs" },
];

function Message({ children, erreur = false }: { children: string; erreur?: boolean }) {
  return (
    <p className={`px-8 py-6 text-sm ${erreur ? "text-red-400" : "text-zinc-500"}`}>
      {children}
    </p>
  );
}

/**
 * The History tab's centre: the detail of one run, or the table of all of
 * them — ticket-427.
 */
export default function HistoriqueView({
  runs,
  loading,
  error,
  runSelectionne,
  onSelectRun,
  tickets,
  project,
}: HistoriqueViewProps) {
  const [vue, setVue] = useState<Vue>("detail");
  // Un run choisi dans la colonne ramène au détail, même depuis le tableau.
  const [selectionVue, setSelectionVue] = useState(runSelectionne);
  if (selectionVue !== runSelectionne) {
    setSelectionVue(runSelectionne);
    setVue("detail");
  }

  const run = runAffiche(runs, runSelectionne);
  const ticket = run ? (tickets.find((t) => t.id === run.ticket_id) ?? null) : null;

  function ouvrir(runId: string) {
    onSelectRun(runId);
    setVue("detail");
  }

  return (
    <div className="flex h-full flex-col bg-zinc-900">
      <div className={`${BAND} justify-between border-b border-zinc-700 px-4`}>
        <RegionTitle>Historique</RegionTitle>
        <div
          role="group"
          aria-label="Vue de l'historique"
          className="flex gap-0.5 rounded-md border border-zinc-800 bg-zinc-900 p-0.5"
        >
          {VUES.map(({ cle, libelle }) => (
            <button
              key={cle}
              type="button"
              aria-pressed={vue === cle}
              onClick={() => setVue(cle)}
              className={`rounded-sm px-3 py-1 text-xs ${
                vue === cle ? "bg-zinc-700 text-zinc-100" : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {libelle}
            </button>
          ))}
        </div>
      </div>

      {error ? (
        <Message erreur>{error}</Message>
      ) : loading && runs.length === 0 ? (
        <Message>Chargement des runs…</Message>
      ) : run === null ? (
        <Message>Aucun run sur ce projet</Message>
      ) : vue === "detail" ? (
        <DetailDuRun run={run} ticket={ticket} project={project} />
      ) : (
        <TousLesRuns runs={runs} tickets={tickets} onOpen={ouvrir} />
      )}
    </div>
  );
}
