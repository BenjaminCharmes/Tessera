import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import { IconDownload, IconProject } from "../../design/icons";
import { useState } from "react";
import { useProjects } from "../../hooks/useProjects";
import type { Project } from "../../types/api";
import CreateProjectModal from "./CreateProjectModal";
import { grouperParCategorie } from "./grouperParCategorie";
import ImportProjectModal from "./ImportProjectModal";
import SkeletonList from "../SkeletonList";
import { lienDuDepot } from "../../lib/lienDuDepot";

interface ProjectNavProps {
  /** Les projets dont un run attend une réponse (ticket-186). */
  enAttente?: ReadonlySet<string>;
  activeProject: Project | null;
  onSelectProject: (project: Project) => void;
  onProjectCreated?: (project: Project) => void;
}

export default function ProjectNav({
  activeProject,
  onSelectProject,
  onProjectCreated,
  enAttente,
}: ProjectNavProps) {
  const { projects, loading, error, refresh } = useProjects();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);

  function handleCreated(project: Project) {
    refresh();
    setShowCreateModal(false);
    onProjectCreated?.(project);
    onSelectProject(project);
  }

  function handleImported(project: Project) {
    refresh();
    setShowImportModal(false);
    onProjectCreated?.(project);
    onSelectProject(project);
  }

  if (error) return <div className="p-4 text-red-400 text-xs">{error}</div>;

  return (
    <>
      <div>
        <div className={`${BAND} justify-between px-3`}>
          <RegionTitle>Projects</RegionTitle>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setShowImportModal(true)}
              className="w-5 h-5 flex items-center justify-center rounded-sm text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800 transition-colors text-xs leading-none"
              title="Importer un projet"
              aria-label="Importer un projet"
            >
              <IconDownload size={14} />
            </button>
            <button
              onClick={() => setShowCreateModal(true)}
              className="w-5 h-5 flex items-center justify-center rounded-sm text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800 transition-colors text-base leading-none"
              title="Nouveau projet"
              aria-label="Créer un projet"
            >
              +
            </button>
          </div>
        </div>
        {loading && <SkeletonList count={3} />}
        {!loading && projects.length === 0 && (
          <div className="px-3 py-4 flex flex-col items-center gap-2 text-center">
            <p className="text-zinc-500 text-xs">
              Aucun projet pour l&apos;instant
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="text-xs px-3 py-1.5 rounded-sm bg-zinc-700 hover:bg-zinc-600 text-zinc-200 transition-colors"
            >
              + Créer un projet
            </button>
            <button
              onClick={() => setShowImportModal(true)}
              className="inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-sm bg-zinc-800 hover:bg-zinc-700 text-zinc-400 transition-colors"
            >
              <IconDownload size={12} /> Importer un projet
            </button>
          </div>
        )}
        {/* Le lien GitHub est un voisin du bouton, pas son enfant : un `<a>`
            dans un `<button>` est du HTML invalide, et deux cibles imbriquées
            se disputent le clic et le focus (ticket-123). */}
        {grouperParCategorie(projects).map((groupe) => (
          <div key={groupe.categorie ?? "__sans__"}>
            {/* Un intitulé de groupe est un titre de région : ADR-026 lui donne
                le neutre, et réserve le violet à l'identité. */}
            <p className="px-3 pb-1 pt-3 text-micro uppercase tracking-wide text-zinc-600">
              {groupe.categorie ?? "Sans catégorie"}
            </p>
            {groupe.projets.map((project) => (
              <div
                key={project.id}
                className={`flex items-center transition-colors ${
                  activeProject?.id === project.id
                    ? "bg-zinc-700 text-white"
                    : "hover:bg-zinc-800 text-zinc-300"
                }`}
              >
                <button
                  type="button"
                  onClick={() => onSelectProject(project)}
                  className="flex min-w-0 flex-1 items-center gap-2 px-3 py-2 text-left"
                >
                  <IconProject size={12} className="shrink-0 text-zinc-500" />
                  <span className="truncate flex-1">{project.name}</span>
                  {/* Ambre : une attente, au sens d'ADR-026. Visible depuis
                      n'importe quel onglet, ce que ni le panneau ni la carte
                      de Supervision ne permettaient (ticket-186). */}
                  {enAttente?.has(project.id) && (
                    <span
                      className="size-1.5 shrink-0 rounded-full bg-amber-400"
                      title="Un agent attend une réponse"
                      aria-label="Un agent attend une réponse"
                    />
                  )}
                </button>
                <LienDuDepot project={project} />
              </div>
            ))}
          </div>
        ))}
      </div>
      {showCreateModal && (
        <CreateProjectModal
          onClose={() => setShowCreateModal(false)}
          onCreated={handleCreated}
        />
      )}
      {showImportModal && (
        <ImportProjectModal
          onClose={() => setShowImportModal(false)}
          onProjectCreated={handleImported}
        />
      )}
    </>
  );
}

/**
 * Le raccourci vers le dépôt d'un projet, quand il en a un d'ouvrable.
 *
 * `github_remote` vaut `owner/repo` : posée telle quelle en `href`, elle se
 * résolvait contre l'origine de l'app et le lien menait à une page de l'IDE
 * (ticket-184).
 */
function LienDuDepot({ project }: { project: Project }) {
  const lien = lienDuDepot(project.github_remote);
  if (!lien) return null;
  return (
    <a
      href={lien}
      target="_blank"
      rel="noopener noreferrer"
      className="shrink-0 px-3 py-2 text-xs leading-none text-zinc-500 transition-colors hover:text-zinc-200"
      title={lien}
      aria-label={`Ouvrir le repo GitHub de ${project.name}`}
    >
      GH
    </a>
  );
}
