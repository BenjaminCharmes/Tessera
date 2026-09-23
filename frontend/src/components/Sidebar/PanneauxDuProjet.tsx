import GitLinkPanel from "./GitLinkPanel";
import PanneauServices from "./PanneauServices";
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
}

export default function PanneauxDuProjet({
  project,
  gitOuvert,
  servicesOuverts,
  services,
  sortieDeService,
}: PanneauxDuProjetProps) {
  if (!project) return null;

  return (
    <>
      {/* Sous l'en-tête, là où l'on vient de cliquer : c'est le reproche fait
          au premier usage — le retour arrivait dans une autre vue. */}
      {/* Le projet qui fait tourner l'IDE n'a pas de bouton : sans
          ouverture d'office, rien n'expliquerait cette absence
          (ticket-152). */}
      {(servicesOuverts || project.fait_tourner_l_ide) &&
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
