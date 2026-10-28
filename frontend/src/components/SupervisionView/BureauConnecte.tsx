import type { ReactNode } from "react";
import type { ReglageSon } from "../BureauView/ColonneAToi";
import BureauView from "../BureauView";
import type { UseSupervisionResult } from "../../hooks/useSupervision";
import { projetsDuBureau } from "../../lib/bureau/projetsDuBureau";
import type { Project, ServiceActif } from "../../types/api";
import EnteteSupervision from "./EnteteSupervision";
import VueVide from "./VueVide";
import { useZoomDuBureau } from "../../hooks/useZoomDuBureau";
import { CommandesDeZoom } from "./ZoomDuBureau";
import type { IssueDuRun } from "./issueDuRun";
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
  /** Le bouton « Fil » d'une pièce : bascule sur la Liste, ce run choisi. */
  onOuvrirFil?: (runId: string) => void;
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
  onOuvrirFil,
}: BureauConnecteProps) {
  const { runs, etatDe, fermerRuns } = supervision;
  const { projets, auRepos } = projetsDuBureau(
    runs,
    etatDe,
    projects.map((p) => p.id),
  );

  const {
    mode: modeDeZoom,
    zoom,
    setMode: setModeDeZoom,
    conteneur,
    contenu,
  } = useZoomDuBureau();

  function ranger(ids: string[]) {
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
        entrees={
          runsClosDe(runs, etatDe).length > 0 ? entreesDuMenu(runs, etatDe) : []
        }
        onFermer={(issue: IssueDuRun | null) =>
          ranger(idsARanger(runs, etatDe, issue))
        }
        selecteur={
          <>
            <CommandesDeZoom
              mode={modeDeZoom}
              zoom={zoom}
              setMode={setModeDeZoom}
            />
            {selecteur}
          </>
        }
      />
      {/* Sans run, le Bureau reste : salles du haut, « À toi », employé de la semaine.
          Seul un canal coupé garde le message plein écran (ticket-636). */}
      {runs.length === 0 && !supervision.connecte ? (
        <VueVide
          connecte={supervision.connecte}
          avecServices={services.length > 0}
        />
      ) : (
        <div ref={conteneur} className="min-h-0 flex-1 overflow-y-auto p-3">
          {/* Le zoom ne touche que le Bureau : le reste de l'app garde sa taille (ticket-657). */}
          <div ref={contenu} data-zoom={zoom} style={{ zoom }}>
            <BureauView
              projets={projets}
              auRepos={auRepos}
              signalServices={supervision.signalServices}
              envoyer={supervision.envoyer}
              son={son}
              onOuvrir={onOuvrirFil}
              onRanger={(runId) => ranger([runId])}
              onOpenProject={onOpenProject && ouvrirLeProjet}
            />
          </div>
        </div>
      )}
    </div>
  );
}
