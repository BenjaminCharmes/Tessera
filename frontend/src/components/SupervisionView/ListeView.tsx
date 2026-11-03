import { useState } from "react";
import type { ReactNode } from "react";
import RunCard from "./RunCard";
import ServicesLances from "./ServicesLances";
import AgentPanel from "../AgentPanel";
import RunHistorique from "../StatsView/RunHistorique";
import EnteteSupervision from "./EnteteSupervision";
import VueVide from "./VueVide";
import { projeter } from "./projeter";
import { entreesDuMenu, idsARanger, runsClosDe } from "./rangement";
import type { IssueDuRun } from "./issueDuRun";
import type { UseSupervisionResult } from "../../hooks/useSupervision";
import type { Project, ServiceActif } from "../../types/api";
import { projetDuRun } from "./projetDuRun";
import { useLimites } from "../../hooks/useLimites";
import { useEtatRun } from "../../hooks/runStore";

/**
 * La Liste : ce que l'IDE est en train de faire, sur tous les projets — ticket-129.
 *
 * `AgentPanel` ne montrait qu'un run, celui du projet actif, et seulement
 * depuis l'onglet qui l'avait lancé. Or le parallélisme réel de Tessera est
 * **entre projets** (ADR-038) : c'est exactement ce que rien n'affichait.
 *
 * Le détail réutilise `AgentPanel` tel quel plutôt qu'un second affichage :
 * deux vues d'un même run divergeraient, et c'est celle qu'on regarde le
 * moins qui dériverait (ADR-034).
 */
interface ListeViewProps {
  supervision: UseSupervisionResult;
  projects: Project[];
  /**
   * Les services lancés, listés à part des runs (ticket-138) : un service
   * n'a ni ticket, ni tours, ni verdict, et ne se termine pas tout seul.
   * Les mêler aux runs donnerait un chrono qui monte indéfiniment à côté de
   * pipelines qui finissent.
   */
  services?: ServiceActif[];
  /** Le sélecteur Bureau / Liste, posé dans la bande d'en-tête (ticket-567). */
  selecteur?: ReactNode;
}

export default function ListeView({
  supervision,
  projects,
  services = [],
  selecteur,
}: ListeViewProps) {
  const { runs, selection, selectionner, etatDe, fermerRuns } = supervision;
  const limites = useLimites();

  // Sélection par défaut calculée avant les cartes triées, pour le runId.
  // On la recalcule après le tri, mais on a besoin du runId pour useEtatRun.
  const runEnAttentePrelim = runs.find(
    (r) => etatDe(r.run_id).pendingQuestion !== null,
  );
  const prelim = runs.find((r) => r.run_id === selection) ?? runEnAttentePrelim ?? runs[0];

  // Souscrit directement au store pour le run sélectionné : les tokens du
  // codeur se mettent à jour sans attendre un re-rendu du parent (ticket-354).
  const etatSelectionne = useEtatRun(prelim?.run_id ?? "");

  // Run affiché en lecture seule — ticket-327.
  const [revisuRun, setRevisuRun] = useState<{ runId: string; ticketId: string } | null>(null);

  // Runs déjà clos, classés par issue (ticket-344).
  const runsClos = runsClosDe(runs, etatDe);

  /** Ferme un lot de runs et nettoie la revue en lecture seule si besoin. */
  function fermerLot(issue: IssueDuRun | null) {
    const aFermer = idsARanger(runs, etatDe, issue);
    const ensemble = new Set(aFermer);
    // Fermer revisuRun si son run est dans le lot.
    if (revisuRun !== null) {
      const runEnRevisu = runs.find((r) => r.db_run_id === revisuRun.runId);
      if (runEnRevisu && ensemble.has(runEnRevisu.run_id)) {
        setRevisuRun(null);
      }
    }
    fermerRuns(aFermer);
  }

  // Les runs qui attendent une réponse passent en tête (ticket-266).
  const runsTries = [...runs].sort((a, b) => {
    const aAttend = etatDe(a.run_id).pendingQuestion !== null;
    const bAttend = etatDe(b.run_id).pendingQuestion !== null;
    if (aAttend === bAttend) return 0;
    return aAttend ? -1 : 1;
  });

  // Un seul « Répondre » plein dans la vue : celui du premier run en attente.
  const premierEnAttente = runsTries.find(
    (r) => etatDe(r.run_id).pendingQuestion !== null,
  );

  // `selectionne` = run affiché dans le panneau de détail.
  const selectionne = prelim;

  /** Sélectionne le run et donne le focus au champ de réponse (ticket-266). */
  function repondre(runId: string) {
    selectionner(runId);
    const input = document.getElementById("dialogue-reponse");
    if (input) {
      input.focus();
    } else {
      requestAnimationFrame(() => {
        document.getElementById("dialogue-reponse")?.focus();
      });
    }
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-zinc-900">
      <EnteteSupervision
        nombreDeRuns={runs.length}
        connecte={supervision.connecte}
        entrees={runsClos.length > 0 ? entreesDuMenu(runs, etatDe) : []}
        onFermer={fermerLot}
        selecteur={selecteur}
      />

      {services.length > 0 ? (
        <ServicesLances
          services={services}
          sortieDe={supervision.sortieDuService}
        />
      ) : null}

      {runs.length === 0 ? (
        <VueVide
          connecte={supervision.connecte}
          avecServices={services.length > 0}
        />
      ) : (
        <div className="grid min-h-0 flex-1 grid-cols-[minmax(240px,340px)_1fr] overflow-hidden">
          <div className="flex flex-col gap-2 overflow-y-auto border-r border-zinc-800 p-3">
            {runsTries.map((run) => {
              const etat = etatDe(run.run_id);
              return (
                <RunCard
                  key={run.run_id}
                  run={run}
                  etat={etat}
                  selectionne={run.run_id === selectionne?.run_id}
                  onSelect={() => {
                    setRevisuRun(null);
                    selectionner(run.run_id);
                  }}
                  plafondUsd={limites?.run_max_budget_usd ?? null}
                  reponsePrincipale={run.run_id === premierEnAttente?.run_id}
                  onRepondre={
                    etat.pendingQuestion !== null
                      ? () => repondre(run.run_id)
                      : undefined
                  }
                  onRevoir={
                    etat.runClosed && run.db_run_id && run.ticket_id
                      ? () =>
                          setRevisuRun({
                            runId: run.db_run_id as string,
                            ticketId: run.ticket_id as string,
                          })
                      : undefined
                  }
                />
              );
            })}
          </div>

          <div className="min-h-0 overflow-hidden">
            {revisuRun ? (
              <RunHistorique
                runId={revisuRun.runId}
                ticketId={revisuRun.ticketId}
                onClose={() => setRevisuRun(null)}
              />
            ) : selectionne ? (
              <AgentPanel
                project={projetDuRun(projects, selectionne)}
                stream={projeter(supervision, selectionne.run_id, etatSelectionne)}
                onRevoirRun={(runId, ticketId) => setRevisuRun({ runId, ticketId })}
              />
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
