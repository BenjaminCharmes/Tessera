import { useProjects } from "../../hooks/useProjects";
import type { Project } from "../../types/api";

interface ProjectNavProps {
  activeProject: Project | null;
  onSelectProject: (project: Project) => void;
}

export default function ProjectNav({
  activeProject,
  onSelectProject,
}: ProjectNavProps) {
  const { projects, loading, error } = useProjects();

  if (loading) return <div className="p-4 text-zinc-500 text-xs">Loading…</div>;
  if (error) return <div className="p-4 text-red-400 text-xs">{error}</div>;
  if (projects.length === 0)
    return <div className="p-4 text-zinc-500 text-xs">No projects found</div>;

  return (
    <div>
      <div className="px-3 py-2 text-xs font-semibold text-zinc-500 uppercase tracking-wider">
        Projects
      </div>
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
  );
}
