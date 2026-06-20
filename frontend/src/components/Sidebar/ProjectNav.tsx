import { useState } from "react";
import { useProjects } from "../../hooks/useProjects";
import type { Project } from "../../types/api";
import CreateProjectModal from "./CreateProjectModal";

interface ProjectNavProps {
  activeProject: Project | null;
  onSelectProject: (project: Project) => void;
}

export default function ProjectNav({
  activeProject,
  onSelectProject,
}: ProjectNavProps) {
  const { projects, loading, error, refresh } = useProjects();
  const [showModal, setShowModal] = useState(false);

  function handleCreated(project: Project) {
    refresh();
    setShowModal(false);
    onSelectProject(project);
  }

  if (loading) return <div className="p-4 text-zinc-500 text-xs">Loading…</div>;
  if (error) return <div className="p-4 text-red-400 text-xs">{error}</div>;

  return (
    <>
      <div>
        <div className="px-3 py-2 flex items-center justify-between">
          <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
            Projects
          </span>
          <button
            onClick={() => setShowModal(true)}
            className="w-5 h-5 flex items-center justify-center rounded text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800 transition-colors text-base leading-none"
            title="Nouveau projet"
            aria-label="Créer un projet"
          >
            +
          </button>
        </div>
        {projects.length === 0 && (
          <div className="px-3 py-2 text-zinc-500 text-xs">
            No projects found
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
            <span className="text-zinc-500 text-xs">◈</span>
            <span className="truncate">{project.name}</span>
          </button>
        ))}
      </div>
      {showModal && (
        <CreateProjectModal
          onClose={() => setShowModal(false)}
          onCreated={handleCreated}
        />
      )}
    </>
  );
}
