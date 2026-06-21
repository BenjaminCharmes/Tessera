import { useState } from "react";
import type { Ticket, TicketDraft } from "../../types/api";
import { api } from "../../lib/api";

type ModalState = "idle" | "planning" | "review" | "creating" | "error";

interface PlanEvolutionModalProps {
  projectId: string;
  onClose: () => void;
  onBatchCreated: (tickets: Ticket[]) => void;
}

const PRIORITY_BADGE: Record<string, string> = {
  critical: "text-red-400",
  high: "text-orange-400",
  medium: "text-yellow-400",
  low: "text-zinc-400",
};

function buildSelectedDrafts(
  drafts: TicketDraft[],
  selected: Set<number>,
): TicketDraft[] {
  const indexMap = new Map<number, number>();
  let newIndex = 0;
  for (let i = 0; i < drafts.length; i++) {
    if (selected.has(i)) {
      indexMap.set(i, newIndex++);
    }
  }
  return drafts
    .filter((_, i) => selected.has(i))
    .map((draft) => ({
      ...draft,
      depends_on_index: draft.depends_on_index
        .filter((dep) => selected.has(dep))
        .map((dep) => indexMap.get(dep)!),
    }));
}

export default function PlanEvolutionModal({
  projectId,
  onClose,
  onBatchCreated,
}: PlanEvolutionModalProps) {
  const [state, setState] = useState<ModalState>("idle");
  const [description, setDescription] = useState("");
  const [summary, setSummary] = useState("");
  const [drafts, setDrafts] = useState<TicketDraft[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);

  async function handlePlan() {
    if (!description.trim()) return;
    setState("planning");
    setError(null);
    try {
      const result = await api.projects.plan(projectId, description);
      setDrafts(result.drafts);
      setSummary(result.summary);
      setSelected(new Set(result.drafts.map((_, i) => i)));
      setState("review");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
      setState("error");
    }
  }

  async function handleCreate() {
    setState("creating");
    setError(null);
    try {
      const selectedDrafts = buildSelectedDrafts(drafts, selected);
      const result = await api.tickets.batch(projectId, selectedDrafts);
      onBatchCreated(result.created);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
      setState("error");
    }
  }

  function toggleSelected(index: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  function handleOverlayClick(e: React.MouseEvent) {
    if (e.target === e.currentTarget) onClose();
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") onClose();
  }

  const isLoading = state === "planning" || state === "creating";
  const selectedCount = selected.size;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={handleOverlayClick}
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-label="Planifier une évolution"
    >
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-6 w-full max-w-lg shadow-xl">
        {/* Step 1: description */}
        {(state === "idle" || state === "planning" || state === "error") && (
          <>
            <h2 className="text-zinc-100 text-base font-semibold mb-1">
              Planifier une évolution
            </h2>
            <p className="text-xs text-zinc-500 mb-4">
              Décris l'évolution souhaitée — l'agent générera une liste de
              tickets ordonnés.
            </p>

            <div className="mb-5">
              <label
                htmlFor="plan-description"
                className="block text-xs text-zinc-400 mb-1"
              >
                Description <span className="text-red-400">*</span>
              </label>
              <textarea
                id="plan-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Je veux ajouter l'authentification OAuth Google…"
                rows={4}
                maxLength={2000}
                className="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-zinc-400 resize-none"
                disabled={isLoading}
                autoFocus
              />
            </div>

            {error && (
              <p className="mb-4 text-xs text-red-400" role="alert">
                {error}
              </p>
            )}

            <div className="flex gap-3 justify-end">
              <button
                type="button"
                onClick={onClose}
                disabled={isLoading}
                className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors disabled:opacity-50"
              >
                Annuler
              </button>
              <button
                type="button"
                onClick={handlePlan}
                disabled={isLoading || !description.trim()}
                className="px-4 py-2 text-sm bg-zinc-700 hover:bg-zinc-600 text-white rounded transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {state === "planning" && (
                  <span className="inline-block w-3 h-3 border-2 border-zinc-400 border-t-white rounded-full animate-spin" />
                )}
                Planifier →
              </button>
            </div>
          </>
        )}

        {/* Step 2: review drafts */}
        {(state === "review" || state === "creating") && (
          <>
            <h2 className="text-zinc-100 text-base font-semibold mb-1">
              {drafts.length} ticket{drafts.length !== 1 ? "s" : ""} générés
            </h2>
            {summary && (
              <p className="text-xs text-zinc-400 mb-4 italic">{summary}</p>
            )}

            <div className="mb-5 space-y-2 max-h-72 overflow-y-auto pr-1">
              {drafts.map((draft, i) => (
                <label
                  key={i}
                  className={`flex items-start gap-3 p-3 rounded border cursor-pointer transition-colors ${
                    selected.has(i)
                      ? "border-zinc-600 bg-zinc-800"
                      : "border-zinc-700 bg-zinc-850 opacity-50"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selected.has(i)}
                    onChange={() => toggleSelected(i)}
                    disabled={state === "creating"}
                    className="mt-0.5 accent-zinc-400"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className={`text-[10px] font-mono uppercase ${PRIORITY_BADGE[draft.priority] ?? "text-zinc-400"}`}
                      >
                        [{draft.priority}]
                      </span>
                      <span className="text-[10px] text-zinc-500 font-mono">
                        {draft.type}
                      </span>
                      <span className="text-sm text-zinc-100 font-medium">
                        {draft.title}
                      </span>
                    </div>
                    {draft.description && (
                      <p className="text-xs text-zinc-400 mt-1 line-clamp-2">
                        {draft.description}
                      </p>
                    )}
                    {draft.depends_on_index.length > 0 && (
                      <p className="text-[10px] text-zinc-500 mt-1">
                        Dépend de :{" "}
                        {draft.depends_on_index
                          .map((dep) => `ticket #${dep + 1}`)
                          .join(", ")}
                      </p>
                    )}
                  </div>
                </label>
              ))}
            </div>

            <div className="flex gap-3 justify-between items-center">
              <button
                type="button"
                onClick={() => setState("idle")}
                disabled={state === "creating"}
                className="px-3 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors disabled:opacity-50"
              >
                ← Retour
              </button>
              <button
                type="button"
                onClick={handleCreate}
                disabled={state === "creating" || selectedCount === 0}
                className="px-4 py-2 text-sm bg-zinc-700 hover:bg-zinc-600 text-white rounded transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {state === "creating" && (
                  <span className="inline-block w-3 h-3 border-2 border-zinc-400 border-t-white rounded-full animate-spin" />
                )}
                Créer {selectedCount} ticket{selectedCount !== 1 ? "s" : ""}{" "}
                sélectionné{selectedCount !== 1 ? "s" : ""}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
