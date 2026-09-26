import GitLinkPanel from "./GitLinkPanel";
import PanneauServices from "./PanneauServices";
import PanneauPipeline from "./PanneauPipeline";
import { useState } from "react";
import type { UseServicesResult } from "../../hooks/useServices";
import type { Project } from "../../types/api";

/**
 * Ce qui se déplie sous l'en-tête du projet — ticket-147.
 *
 * Deux panneaux qui suivent le même motif : ouverts par leur bouton, bornés
 * en hauteur, refermés le reste du temps. Extraits de `Sidebar` quand le
 * second l'a fait dépasser deux cents lignes.
 */
interface PanneauxDuProjetProps {
  project: Project | null;
  gitOuvert: boolean;
  servicesOuverts: boolean;
  services?: UseServicesResult;
  sortieDeService?: (projectId: string, nom: string) => string[];
  /** Un run tourne sur ce projet : le pipeline se règle en lecture seule (ticket-196). */
  runEnCours?: boolean;
}

export default function PanneauxDuProjet({
  project,
  gitOuvert,
  servicesOuverts,
  services,
  sortieDeService,
  runEnCours = false,
}: PanneauxDuProjetProps) {
  const [pipelineOuvert, setPipelineOuvert] = useState(false);
  if (!project) return null;

  return (
    <>
      <button
        type="button"
        onClick={() => setPipelineOuvert((v) => !v)}
        aria-expanded={pipelineOuvert}
        className="w-full px-3 py-1 text-left text-mini text-zinc-500 hover:text-zinc-300"
      >
        Pipeline
      </button>
      {pipelineOuvert && (
        <PanneauPipeline projectId={project.id} runEnCours={runEnCours} />
      )}
      {/* Sous l'en-tête, là où l'on vient de cliquer : c'est le reproche fait
          au premier usage — le retour arrivait dans une autre vue. */}
      {/* Le projet qui fait tourner l'IDE n'a pas de bouton : sans
          ouverture d'office, rien n'expliquerait cette absence
          (ticket-152). */}
      {/* Ouvert aussi dès qu'un service vit ou vient de mourir : après un
          rechargement, `servicesOuverts` repart à faux et le seul clic qui
          rouvrait le panneau arrêtait le service (ticket-155). */}
      {/* Ouvert aussi quand rien n'est déclaré : `RienDeclare` n'était
          atteignable par personne, le seul geste qui ouvrait ce panneau étant
          le bouton de lancement — que ces projets n'ont pas (ticket-156). */}
      {(servicesOuverts ||
        project.fait_tourner_l_ide ||
        services?.declare === false ||
        services?.enCours ||
        services?.enEchec) &&
      services &&
      sortieDeService ? (
        <div className="max-h-72 overflow-y-auto overflow-x-hidden border-b border-zinc-800">
          <PanneauServices
            services={services}
            sortieDe={sortieDeService}
            projectId={project.id}
            cheminDuProjet={project.path ?? null}
            faitTournerLIde={project.fait_tourner_l_ide ?? false}
          />
        </div>
      ) : null}

      {gitOuvert ? (
        <div className="max-h-64 overflow-y-auto overflow-x-hidden border-b border-zinc-800">
          <GitLinkPanel project={project} />
        </div>
      ) : null}
    </>
  );
}
