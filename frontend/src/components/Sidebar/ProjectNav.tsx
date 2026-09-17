import RegionTitle from "../../design/RegionTitle";
import { IconDownload, IconProject } from "../../design/icons";
import { useState } from "react";
import { useProjects } from "../../hooks/useProjects";
import type { Project } from "../../types/api";
import CreateProjectModal from "./CreateProjectModal";
import ImportProjectModal from "./ImportProjectModal";
import SkeletonList from "../SkeletonList";

interface ProjectNavProps {
  activeProject: Project | null;
  onSelectProject: (project: Project) => void;
  onProjectCreated?: (project: Project) => void;
}

export default function ProjectNav({
  activeProject,
  onSelectProject,
  onProjectCreated,
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
        <div className="px-3 py-2 flex items-center justify-between">
          <RegionTitle>
            Projects
          </RegionTitle>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setShowImportModal(true)}
              className="w-5 h-5 flex items-center justify-center rounded text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800 transition-colors text-xs leading-none"
              title="Importer un projet"
              aria-label="Importer un projet"
            >
              <IconDownload size={14} />
            </button>
            <button
              onClick={() => setShowCreateModal(true)}
              className="w-5 h-5 flex items-center justify-center rounded text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800 transition-colors text-base leading-none"
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
              className="text-xs px-3 py-1.5 rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-200 transition-colors"
            >
              + Créer un projet
            </button>
            <button
              onClick={() => setShowImportModal(true)}
              className="text-xs px-3 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-400 transition-colors"
            >
              <IconDownload size={12} /> Importer un projet
            </button>
          </div>
        )}
        {projects.map((project) => (
          <button
            key={project.id}
            onClick={() => onSelectProject(project)}
            className={`w-full text-left px-3 py-2 flex items-center gap-2 transition-colors ${
              activeProject?.id === project.id
                ? "bg-zinc-700 text-white"
                : "hover:bg-zinc-800 text-zinc-300"
            }`}
          >
            <IconProject size={12} className="shrink-0 text-zinc-500" />
            <span className="truncate flex-1">{project.name}</span>
            {project.github_remote && (
              <a
                href={project.github_remote}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="text-zinc-500 hover:text-zinc-200 transition-colors text-xs leading-none shrink-0"
                title={project.github_remote}
                aria-label={`Ouvrir le repo GitHub de ${project.name}`}
              >
                GH
              </a>
            )}
          </button>
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
