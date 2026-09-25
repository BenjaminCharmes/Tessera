import AgentBadge from "../../design/AgentBadge";
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
  onSelect?: (role: string) => void;
  selectionne?: boolean;
}

function AgentRow({
  agent,
  deleting,
  onDelete,
  onSelect,
  selectionne = false,
}: AgentRowProps) {
  return (
    <div
      className={`group flex items-center gap-2 border-b border-zinc-800 px-3 py-2 transition-colors ${
        selectionne ? "bg-violet-500/10" : "hover:bg-zinc-800"
      }`}
    >
      {/* Le nom ouvre la définition au centre : le prompt système décide de
          tout ce que fait l'agent, et il n'était lisible nulle part
          (ticket-076). */}
      <button
        type="button"
        onClick={() => onSelect?.(agent.role)}
        title={agent.prompt_preview || undefined}
        className={`min-w-0 flex-1 truncate text-left font-mono text-mini transition-colors ${
          selectionne ? "text-violet-200" : "text-zinc-200 hover:text-violet-200"
        }`}
      >
        {agent.role}
      </button>
      <AgentBadge moment={agent.moment ?? "jamais"} />
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
  onSelect?: (role: string) => void;
  selectionne?: string | null;
}

export default function AgentList({
  onAgentCreated,
  onSelect,
  selectionne = null,
}: AgentListProps) {
  const { agents, loading, error, refresh } = useAgents();
  const [showModal, setShowModal] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [aConfirmer, setAConfirmer] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Rien ne se supprime sans un second geste. Un clic sur la croix retirait le
  // prompt de l'agent — sa définition entière, donc tout ce qui détermine son
  // comportement — sans rien demander (ticket-080).
  async function confirmerSuppression() {
    const role = aConfirmer;
    if (!role) return;
    setAConfirmer(null);
    await handleDelete(role);
  }

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
              onSelect={onSelect}
          selectionne={agent.role === selectionne}
          onDelete={setAConfirmer}
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

      {aConfirmer && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Confirmer la suppression"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
        >
          <div className="w-full max-w-sm rounded-lg border border-zinc-700 bg-zinc-900 p-5 shadow-xl">
            <h2 className="mb-2 text-sm font-medium text-zinc-100">
              Supprimer « {aConfirmer} » ?
            </h2>
            <p className="mb-4 text-xs text-zinc-400">
              Son prompt système est effacé du disque. C'est la définition
              entière de l'agent — tout ce qui détermine son comportement — et
              elle ne se récupère pas depuis l'IDE.
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setAConfirmer(null)}
                className="px-3 py-1.5 text-xs text-zinc-400 transition-colors hover:text-zinc-200"
              >
                Annuler
              </button>
              <button
                type="button"
                onClick={() => void confirmerSuppression()}
                className="rounded-sm bg-red-800 px-3 py-1.5 text-xs text-red-50 transition-colors hover:bg-red-700"
              >
                Supprimer définitivement
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
