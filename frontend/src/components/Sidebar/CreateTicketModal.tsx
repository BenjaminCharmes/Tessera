import { useState } from "react";
import type { Ticket, TicketPriority, TicketType } from "../../types/api";
import { api } from "../../lib/api";

interface CreateTicketModalProps {
  projectId: string;
  onClose: () => void;
  onCreated: (ticket: Ticket) => void;
}

const TYPES: { value: TicketType; label: string }[] = [
  { value: "feat", label: "feat — nouvelle fonctionnalité" },
  { value: "fix", label: "fix — correction de bug" },
  { value: "chore", label: "chore — maintenance / CI" },
  { value: "design", label: "design — architecture" },
  { value: "docs", label: "docs — documentation" },
];

const PRIORITIES: { value: TicketPriority; label: string }[] = [
  { value: "critical", label: "critical" },
  { value: "high", label: "high" },
  { value: "medium", label: "medium" },
  { value: "low", label: "low" },
];

export default function CreateTicketModal({
  projectId,
  onClose,
  onCreated,
}: CreateTicketModalProps) {
  const [title, setTitle] = useState("");
  const [type, setType] = useState<TicketType>("feat");
  const [priority, setPriority] = useState<TicketPriority>("medium");
  const [description, setDescription] = useState("");
  const [titleError, setTitleError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      setTitleError("Le titre est requis");
      return;
    }
    if (title.length > 100) {
      setTitleError("Le titre ne doit pas dépasser 100 caractères");
      return;
    }
    setTitleError(null);
    setApiError(null);
    setLoading(true);
    try {
      const ticket = await api.tickets.create(projectId, {
        title: title.trim(),
        type,
        priority,
        description,
      });
      onCreated(ticket);
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  }

  function handleOverlayClick(e: React.MouseEvent) {
    if (e.target === e.currentTarget) onClose();
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") onClose();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={handleOverlayClick}
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-label="Créer un ticket"
    >
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-6 w-full max-w-md shadow-xl">
        <h2 className="text-zinc-100 text-base font-semibold mb-4">
          Nouveau ticket
        </h2>
        <form onSubmit={handleSubmit} noValidate>
          <div className="mb-4">
            <label
              htmlFor="ticket-title"
              className="block text-xs text-zinc-400 mb-1"
            >
              Titre <span className="text-red-400">*</span>
            </label>
            <input
              id="ticket-title"
              type="text"
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                setTitleError(null);
              }}
              placeholder="Implémenter la fonctionnalité X"
              maxLength={100}
              className="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-zinc-400"
              disabled={loading}
              autoFocus
            />
            {titleError && (
              <p className="mt-1 text-xs text-red-400" role="alert">
                {titleError}
              </p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3 mb-4">
            <div>
              <label
                htmlFor="ticket-type"
                className="block text-xs text-zinc-400 mb-1"
              >
                Type
              </label>
              <select
                id="ticket-type"
                value={type}
                onChange={(e) => setType(e.target.value as TicketType)}
                className="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-zinc-400"
                disabled={loading}
              >
                {TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label
                htmlFor="ticket-priority"
                className="block text-xs text-zinc-400 mb-1"
              >
                Priorité
              </label>
              <select
                id="ticket-priority"
                value={priority}
                onChange={(e) => setPriority(e.target.value as TicketPriority)}
                className="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-zinc-400"
                disabled={loading}
              >
                {PRIORITIES.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="mb-5">
            <label
              htmlFor="ticket-description"
              className="block text-xs text-zinc-400 mb-1"
            >
              Description{" "}
              <span className="text-zinc-600">(Markdown, optionnel)</span>
            </label>
            <textarea
              id="ticket-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="## Contexte&#10;&#10;## Tâches&#10;&#10;## Critères d'acceptation"
              maxLength={2000}
              rows={5}
              className="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-zinc-400 resize-none font-mono"
              disabled={loading}
            />
          </div>

          {apiError && (
            <p className="mb-4 text-xs text-red-400" role="alert">
              {apiError}
            </p>
          )}

          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors disabled:opacity-50"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 text-sm bg-zinc-700 hover:bg-zinc-600 text-white rounded transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {loading && (
                <span className="inline-block w-3 h-3 border-2 border-zinc-400 border-t-white rounded-full animate-spin" />
              )}
              Créer
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
