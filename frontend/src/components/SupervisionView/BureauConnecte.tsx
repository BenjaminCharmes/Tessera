import { useState } from "react";
import type { ReactNode } from "react";
import type { ReglageSon } from "../BureauView/ColonneAToi";
import Button from "../../design/ui/Button";
import AgentPanel from "../AgentPanel";
import BureauView from "../BureauView";
import { useEtatRun } from "../../hooks/runStore";
import type { UseSupervisionResult } from "../../hooks/useSupervision";
import { projetsDuBureau } from "../../lib/bureau/projetsDuBureau";
import type { Project, ServiceActif } from "../../types/api";
import EnteteSupervision from "./EnteteSupervision";
import VueVide from "./VueVide";
import type { IssueDuRun } from "./issueDuRun";
import { projeter } from "./projeter";
import { projetDuRun } from "./projetDuRun";
import { entreesDuMenu, idsARanger, runsClosDe } from "./rangement";

interface BureauConnecteProps {
  supervision: UseSupervisionResult;
  projects: Project[];
  services?: ServiceActif[];
  son: ReglageSon;
  /** Le sélecteur Bureau / Liste, posé dans la bande d'en-tête. */
  selecteur?: ReactNode;
  /** La porte d'une pièce : choisit le projet et ouvre l'onglet Tickets (ticket-602). */
  onOpenProject?: (project: Project) => void;
}

/**
 * Le Bureau branché sur la supervision (ticket-567) : les mêmes runs, le même
 * store et les mêmes fonctions de rangement que la Liste (ADR-034). La rangée
 * des services n'y est plus : la baie de chaque pièce les montre déjà.
 */
export default function BureauConnecte({
  supervision,
  projects,
  services = [],
  son,
  selecteur,
  onOpenProject,
}: BureauConnecteProps) {
  const { runs, etatDe, fermerRuns } = supervision;
  const [filOuvert, setFilOuvert] = useState<string | null>(null);
  const run = runs.find((r) => r.run_id === filOuvert) ?? null;
  const etatDuFil = useEtatRun(run?.run_id ?? "");
  const { projets, auRepos } = projetsDuBureau(
    runs,
    etatDe,
    projects.map((p) => p.id),
  );

  function ranger(ids: string[]) {
    if (filOuvert !== null && ids.includes(filOuvert)) setFilOuvert(null);
    fermerRuns(ids);
  }

  // Le Bureau nomme ses projets par identifiant : un identifiant inconnu n'ouvre rien.
  function ouvrirLeProjet(id: string) {
    const projet = projects.find((p) => p.id === id);
    if (projet) onOpenProject?.(projet);
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-zinc-900">
      <EnteteSupervision
        nombreDeRuns={runs.length}
        connecte={supervision.connecte}
        entrees={runsClosDe(runs, etatDe).length > 0 ? entreesDuMenu(runs, etatDe) : []}
        onFermer={(issue: IssueDuRun | null) => ranger(idsARanger(runs, etatDe, issue))}
        selecteur={selecteur}
      />
      {runs.length === 0 ? (
        <VueVide connecte={supervision.connecte} avecServices={services.length > 0} />
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          <BureauView
            projets={projets}
            auRepos={auRepos}
            signalServices={supervision.signalServices}
            envoyer={supervision.envoyer}
            son={son}
            onOuvrir={setFilOuvert}
            onRanger={(runId) => ranger([runId])}
            onOpenProject={onOpenProject && ouvrirLeProjet}
          />
        </div>
      )}
      {run && (
        <div className="flex h-1/2 min-h-0 flex-col border-t border-zinc-800">
          <div className="flex items-center justify-between px-3 py-1.5">
            <span className="text-micro text-zinc-500">Fil de {run.ticket_id ?? run.mode}</span>
            <Button taille="compact" variante="discret" onClick={() => setFilOuvert(null)}>
              Masquer le fil
            </Button>
          </div>
          <div className="min-h-0 flex-1 overflow-hidden">
            <AgentPanel
              project={projetDuRun(projects, run)}
              stream={projeter(supervision, run.run_id, etatDuFil)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
