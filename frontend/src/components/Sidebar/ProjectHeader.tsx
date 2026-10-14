import { useState } from "react";
import BoutonServices from "./BoutonServices";
import SelecteurDeProjet from "./SelecteurDeProjet";
import SignalementModal from "./SignalementModal";
import { titreDuProjet } from "./titreDuProjet";
import StatusPill from "../../design/ui/StatusPill";
import type { UseServicesResult } from "../../hooks/useServices";
import { BAND } from "../../design/layout";
import type { Project } from "../../types/api";

/**
 * En-tête du projet actif, épinglé au-dessus de la colonne qui défile
 * (ticket-065).
 *
 * Les actions d'un projet — lier un dépôt, choisir le mode des artefacts, le
 * retirer de l'IDE — vivaient sous la liste des tickets. Sur un projet qui en
 * a trente, elles étaient à un écran et demi de défilement, sans que rien
 * n'annonce leur existence. Elles remontent ici, à un endroit qui ne bouge
 * jamais.
 *
 * L'ouverture dans VSCode est un simple lien `vscode://` : c'est le geste
 * central du pivot cockpit — Tessera pilote, VSCode édite — et il ne coûte
 * aucun aller-retour avec le backend.
 */
interface ProjectHeaderProps {
  project: Project | null;
  gitOuvert: boolean;
  onBasculerGit: () => void;
  /**
   * Les services du projet (ticket-138). Absent : aucun bouton — c'est le cas
   * des vues qui n'ont pas de projet à lancer.
   */
  services?: UseServicesResult;
  /** Ouvre le panneau des services, pour que le clic ait un effet visible. */
  onOuvrirLesServices?: () => void;
  /** Change de projet depuis l'en-tête (ticket-174). Absent : le nom reste un titre. */
  onSelectProject?: (project: Project) => void;
  /** Un run tourne sur ce projet : une pastille le dit à côté du nom (ticket-441). */
  runEnCours?: boolean;
}

/** Le projet qui reçoit les signalements : y signaler depuis lui-même n'a pas de sens. */
const PROJET_CIBLE_DES_SIGNALEMENTS = "ide-core";

/** `vscode://file/` attend des séparateurs POSIX, y compris sous Windows. */
function lienVSCode(chemin: string): string {
  return `vscode://file/${chemin.replace(/\\/g, "/")}`;
}

export default function ProjectHeader({
  project,
  gitOuvert,
  onBasculerGit,
  services,
  onOuvrirLesServices,
  onSelectProject,
  runEnCours = false,
}: ProjectHeaderProps) {
  const [signalementOuvert, setSignalementOuvert] = useState(false);

  if (!project) {
    return (
      <header className={`${BAND} border-b border-zinc-800 px-3`}>
        <p className="text-xs text-zinc-500">Aucun projet sélectionné</p>
      </header>
    );
  }

  return (
    <header className="shrink-0 border-b border-zinc-800">
      {/* Deux lignes : quatre boutons sur la même rangée que le nom le
          tronquaient en « A… » dans une colonne de 280 px. La première ligne
          reste la bande commune, alignée avec celles du centre et de la
          colonne de droite ; les actions passent dessous. */}
      <div className={`${BAND} gap-2 px-3`}>
        {/* Le nom est le déclencheur : changer de projet n'ajoute aucun
            bouton à la rangée d'actions (ticket-174). Sans `onSelectProject`
            — les vues qui n'en ont pas — il reste un titre. */}
        {onSelectProject ? (
          <SelecteurDeProjet
            project={project}
            onSelectProject={onSelectProject}
          />
        ) : (
          <h2
            className="truncate text-sm font-medium text-zinc-100"
            title={titreDuProjet(project)}
          >
            {project.name}
          </h2>
        )}
        {/* Un mot, pas seulement une couleur : l'état se lit sans la teinte. */}
        {runEnCours ? (
          <span className="shrink-0">
            <StatusPill etat="en-cours" libelle="run en cours" />
          </span>
        ) : null}
      </div>

      <div
        role="toolbar"
        aria-label="Actions du projet"
        className="flex flex-wrap items-center gap-1.5 px-3 pb-2"
      >
        {services && !project.fait_tourner_l_ide ? (
          <BoutonServices
            services={services}
            libelleDuProjet={project.name}
            onOuvrirLePanneau={onOuvrirLesServices}
          />
        ) : null}
        {/* Un projet sans chemin ne coûte que ce bouton : le faire planter
            emportait toute la colonne derrière l'ErrorBoundary. */}
        {project.path ? (
          <a
            href={lienVSCode(project.path)}
            className="whitespace-nowrap rounded-sm border border-zinc-700 px-2 py-1 text-mini text-zinc-300 transition-colors hover:border-zinc-500 hover:text-zinc-100"
          >
            VSCode
          </a>
        ) : null}
        <button
          type="button"
          onClick={onBasculerGit}
          aria-expanded={gitOuvert}
          className={`whitespace-nowrap rounded border px-2 py-1 text-mini transition-colors ${
            gitOuvert
              ? "border-zinc-500 bg-zinc-800 text-zinc-100"
              : "border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:text-zinc-100"
          }`}
        >
          Git
        </button>
        {project.id !== PROJET_CIBLE_DES_SIGNALEMENTS ? (
          <button
            type="button"
            onClick={() => setSignalementOuvert(true)}
            className="whitespace-nowrap rounded border border-zinc-700 px-2 py-1 text-mini text-zinc-300 transition-colors hover:border-zinc-500 hover:text-zinc-100"
          >
            Signaler
          </button>
        ) : null}
      </div>
      {signalementOuvert ? (
        <SignalementModal
          project={project}
          onClose={() => setSignalementOuvert(false)}
        />
      ) : null}
    </header>
  );
}
