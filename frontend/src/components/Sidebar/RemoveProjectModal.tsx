import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { Project, RemovalPlan } from "../../types/api";

interface RemoveProjectModalProps {
  project: Project;
  onClose: () => void;
  onRemoved: () => void;
}

/**
 * Retirer un projet de l'IDE (ticket-063).
 *
 * Deux actions distinctes, jamais confondues : *retirer* préserve les
 * fichiers, *supprimer* les efface. La différence compte surtout pour un
 * projet lié en symlink, dont le dossier est celui de travail de
 * l'utilisateur — la modale nomme donc toujours le chemin réellement visé.
 */
export default function RemoveProjectModal({
  project,
  onClose,
  onRemoved,
}: RemoveProjectModalProps) {
  const [plan, setPlan] = useState<RemovalPlan | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.git
      .removalPlan(project.id)
      .then((p) => !cancelled && setPlan(p))
      .catch((err: unknown) => {
        if (!cancelled) setErrorMessage(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [project.id]);

  async function run(action: "detach" | "remove") {
    setBusy(true);
    setErrorMessage(null);
    try {
      if (action === "detach") await api.git.detach(project.id);
      else await api.git.remove(project.id);
      onRemoved();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div
        role="dialog"
        aria-label={`Retirer ${project.id}`}
        className="w-full max-w-md rounded border border-zinc-700 bg-zinc-900 p-4 text-sm text-zinc-200"
      >
        <h2 className="mb-2 text-base font-medium">Retirer « {project.id} »</h2>

        {plan && (
          <div className="mb-3 space-y-1 text-xs text-zinc-400">
            <p>
              Dossier visé : <code className="break-all">{plan.real_path}</code>
            </p>
            {plan.is_symlink && (
              <p className="text-amber-400">
                Ce projet est un lien vers un dossier réel. Rien de ce qui suit
                ne touchera à son contenu.
              </p>
            )}
            {plan.unpushed_commits > 0 && (
              <p className="text-amber-400">
                {plan.unpushed_commits} commit(s) non poussé(s) — ils seraient
                perdus par une suppression définitive.
              </p>
            )}
          </div>
        )}

        <div className="space-y-2">
          <button
            type="button"
            onClick={() => void run("detach")}
            disabled={busy}
            className="w-full rounded bg-zinc-700 px-3 py-1.5 text-left hover:bg-zinc-600 disabled:opacity-40"
          >
            Retirer de l'IDE
            <span className="block text-xs text-zinc-400">
              {plan?.is_symlink
                ? "Supprime le lien. Le dossier d'origine reste intact."
                : "Déplace le dossier hors du workspace. Rien n'est perdu."}
            </span>
          </button>

          {!confirmDelete ? (
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              disabled={busy}
              className="w-full rounded border border-red-900 px-3 py-1.5 text-left text-red-300 hover:bg-red-950/40 disabled:opacity-40"
            >
              Supprimer définitivement
              <span className="block text-xs text-red-400/80">
                {plan?.is_symlink
                  ? "Supprime le lien uniquement — jamais le dossier d'origine."
                  : "Efface le dossier. Irréversible."}
              </span>
            </button>
          ) : (
            <div className="rounded border border-red-900 bg-red-950/40 p-2">
              <p className="mb-2 text-xs text-red-300">
                {plan?.is_symlink
                  ? `Le lien sera supprimé. ${plan.real_path} ne sera pas touché.`
                  : `${plan?.real_path} sera effacé définitivement.`}
              </p>
              <button
                type="button"
                onClick={() => void run("remove")}
                disabled={busy}
                className="rounded bg-red-800 px-3 py-1 text-red-50 hover:bg-red-700 disabled:opacity-40"
              >
                Confirmer la suppression
              </button>
            </div>
          )}
        </div>

        {errorMessage && (
          <p className="mt-2 break-words text-xs text-amber-300">{errorMessage}</p>
        )}

        <button
          type="button"
          onClick={onClose}
          disabled={busy}
          className="mt-3 text-xs text-zinc-500 hover:text-zinc-300"
        >
          Annuler
        </button>
      </div>
    </div>
  );
}
