import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import { IconDownload } from "../../design/icons";
import { useState } from "react";
import { useCategoriesRepliees } from "../../hooks/useCategoriesRepliees";
import { useProjects } from "../../hooks/useProjects";
import type { Project } from "../../types/api";
import CreateProjectModal from "./CreateProjectModal";
import EnTeteDeCategorie from "./EnTeteDeCategorie";
import { grouperParCategorie } from "./grouperParCategorie";
import ImportProjectModal from "./ImportProjectModal";
import LigneDeProjet from "./LigneDeProjet";
import SkeletonList from "../SkeletonList";

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
  const { estRepliee, basculer } = useCategoriesRepliees();
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
        {grouperParCategorie(projects).map((groupe) => {
          const repliee = estRepliee(groupe.categorie);
          // Le projet actif reste affiché sous un titre replié : on ne perd
          // jamais de vue où l'on travaille (ticket-400).
          const visibles = repliee
            ? groupe.projets.filter((p) => p.id === activeProject?.id)
            : groupe.projets;
          return (
            <div key={groupe.categorie ?? "__sans__"}>
              <EnTeteDeCategorie
                categorie={groupe.categorie}
                projets={groupe.projets}
                repliee={repliee}
                onBasculer={() => basculer(groupe.categorie)}
              />
              {visibles.map((project) => (
                <LigneDeProjet
                  key={project.id}
                  project={project}
                  active={activeProject?.id === project.id}
                  enAttente={enAttente?.has(project.id) ?? false}
                  onSelect={() => onSelectProject(project)}
                />
              ))}
            </div>
          );
        })}
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
