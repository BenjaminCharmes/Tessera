import { useState } from "react";
import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import { Chargement, Erreur, Vide } from "../../design/ui/ViewState";
import ViewSwitcher, { type OptionVue } from "../../design/ui/ViewSwitcher";
import type { PipelineRun, Project, Ticket } from "../../types/api";
import DetailDuRun from "./DetailDuRun";
import TousLesRuns from "./TousLesRuns";
import { runAffiche, runsDeTicket } from "./runs";

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

const VUES: OptionVue<Vue>[] = [
  { valeur: "detail", libelle: "Détail du run" },
  { valeur: "tous", libelle: "Tous les runs" },
];

/**
 * The History tab's centre: the detail of one run, or the table of all of
 * them — ticket-427.
 */
export default function HistoriqueView({
  runs: tousLesRuns,
  loading,
  error,
  runSelectionne,
  onSelectRun,
  tickets,
  project,
}: HistoriqueViewProps) {
  // Une file de tickets ne compte pas pour un run de plus : ses enfants suffisent.
  const runs = runsDeTicket(tousLesRuns);
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
        <ViewSwitcher
          options={VUES}
          valeur={vue}
          onChange={setVue}
          label="Vue de l'historique"
        />
      </div>

      {error ? (
        <Erreur message={error} onRetry={() => window.location.reload()} />
      ) : loading && runs.length === 0 ? (
        <Chargement />
      ) : run === null ? (
        <Vide titre="Aucun run sur ce projet" phrase="Lancez un ticket pour voir son historique ici." />
      ) : vue === "detail" ? (
        <DetailDuRun run={run} ticket={ticket} project={project} />
      ) : (
        <TousLesRuns
          runs={runs}
          tickets={tickets}
          projectId={project?.id ?? null}
          onOpen={ouvrir}
        />
      )}
    </div>
  );
}
