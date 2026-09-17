import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import { IconCross } from "../../design/icons";
import { useState } from "react";
import { api } from "../../lib/api";
import { useAgents } from "../../hooks/useAgents";
import type { AgentInfo } from "../../types/api";
import AgentCreatorModal from "./AgentCreatorModal";

interface AgentRowProps {
  agent: AgentInfo;
  deleting: boolean;
  onDelete: (role: string) => void;
}

function AgentRow({ agent, deleting, onDelete }: AgentRowProps) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 border-b border-zinc-800 hover:bg-zinc-800 transition-colors group">
      <span
        className="flex-1 min-w-0 text-mini font-mono text-zinc-200 truncate"
        title={agent.prompt_preview || undefined}
      >
        {agent.role}
      </span>
      <span
        className={`shrink-0 text-micro font-medium px-1.5 py-0.5 rounded ${
          agent.is_builtin
            ? "bg-blue-900 text-blue-300"
            : "bg-green-900 text-green-300"
        }`}
      >
        {agent.is_builtin ? "built-in" : "custom"}
      </span>
      {!agent.is_builtin && (
        <button
          onClick={() => onDelete(agent.role)}
          disabled={deleting}
          title={`Supprimer ${agent.role}`}
          className="shrink-0 text-zinc-600 hover:text-red-400 transition-colors disabled:opacity-40 text-xs opacity-0 group-hover:opacity-100"
          aria-label={`Supprimer ${agent.role}`}
        >
          <IconCross size={14} />
        </button>
      )}
    </div>
  );
}

interface AgentListProps {
  onAgentCreated: (role: string) => void;
}

export default function AgentList({ onAgentCreated }: AgentListProps) {
  const { agents, loading, error, refresh } = useAgents();
  const [showModal, setShowModal] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleDelete(role: string) {
    setDeleting(role);
    setDeleteError(null);
    try {
      await api.agents.remove(role);
      refresh();
    } catch (err: unknown) {
      setDeleteError(
        err instanceof Error ? err.message : "Erreur lors de la suppression",
      );
    } finally {
      setDeleting(null);
    }
  }

  function handleCreated(role: string) {
    setShowModal(false);
    refresh();
    onAgentCreated(role);
  }

  if (loading) {
    return (
      <div className="p-4 text-zinc-500 text-xs">Chargement des agents…</div>
    );
  }

  if (error) {
    return <div className="p-4 text-red-400 text-xs">{error}</div>;
  }

  return (
    <div className="flex flex-col h-full">
      <div className={`${BAND} justify-between border-b border-zinc-700 px-3`}>
        <RegionTitle>
          Agents
        </RegionTitle>
        <button
          onClick={() => setShowModal(true)}
          title="Créer un agent"
          className="text-zinc-500 hover:text-zinc-200 text-xs transition-colors"
        >
          + Nouveau
        </button>
      </div>

      {deleteError && (
        <div className="px-3 py-2 text-xs text-red-400" role="alert">
          {deleteError}
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {agents.length === 0 ? (
          <div className="p-4 text-zinc-500 text-xs">
            Aucun agent configuré.
          </div>
        ) : (
          agents.map((agent) => (
            <AgentRow
              key={agent.role}
              agent={agent}
              deleting={deleting === agent.role}
              onDelete={handleDelete}
            />
          ))
        )}
      </div>

      {showModal && (
        <AgentCreatorModal
          onClose={() => setShowModal(false)}
          onCreated={handleCreated}
        />
      )}
    </div>
  );
}
