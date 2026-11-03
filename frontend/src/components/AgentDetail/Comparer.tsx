import { useMemo } from "react";
import { api } from "../../lib/api";
import { useResource } from "../../hooks/useResource";
import type { ProjectAgents } from "../../types/api";
import { chiffresDuRole } from "./chiffres";
import { useChiffresAgents } from "./useChiffresAgents";

const COLONNES = "grid grid-cols-[10rem_minmax(0,1fr)_6rem_6rem] gap-3 px-3";

/**
 * Tous les rôles actifs du projet côte à côte : modèle, appels et coût sur
 * 30 jours (ticket-429). Un clic sur une ligne ouvre la fiche du rôle.
 */
export default function Comparer({
  projectId,
  onOpen,
}: {
  projectId: string | null;
  onOpen: (role: string) => void;
}) {
  const fetcher = useMemo(
    () => (projectId ? () => api.git.agents(projectId) : null),
    [projectId],
  );
  const charge = useResource<ProjectAgents | null>(fetcher, null);
  const { lignes, loading } = useChiffresAgents(projectId);

  if (!projectId) {
    return (
      <p className="px-4 py-3 text-xs text-zinc-500">
        Ouvre un projet pour comparer ses rôles.
      </p>
    );
  }
  if (charge.error) {
    return (
      <p className="px-4 py-3 text-xs text-red-400">
        Impossible de lire les rôles du projet : {charge.error}
      </p>
    );
  }
  const roles = (charge.data?.agents ?? []).filter((a) => a.active);

  return (
    <div className="min-h-0 flex-1 overflow-auto p-4">
      <p className="mb-3 text-xs text-zinc-400">
        Les rôles actifs du projet, sur les 30 derniers jours.
      </p>
      <div className="overflow-hidden rounded-sm border border-zinc-800">
        <div
          className={`${COLONNES} bg-zinc-950 py-2 text-micro uppercase tracking-wide text-zinc-500`}
        >
          <span>Rôle</span>
          <span>Modèle</span>
          <span>Appels</span>
          <span>Coût</span>
        </div>
        {roles.map((a) => {
          const c = chiffresDuRole(lignes, a.role);
          return (
            <button
              key={a.role}
              type="button"
              onClick={() => onOpen(a.role)}
              className={`${COLONNES} w-full border-t border-zinc-800 py-2 text-left text-xs text-zinc-200 transition-colors hover:bg-zinc-800`}
            >
              <span>{a.role}</span>
              <span className="truncate text-zinc-400">{a.model}</span>
              <span className="text-zinc-400">{loading ? "…" : c.appels}</span>
              <span className="text-zinc-400">{loading ? "…" : c.cout}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
