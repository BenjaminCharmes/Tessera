import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/api";
import { useGitStatus } from "../../hooks/useGitStatus";
import RemoveProjectModal from "./RemoveProjectModal";
import type { ArtifactMode, ArtifactModeState, Project } from "../../types/api";

interface GitLinkPanelProps {
  project: Project | null;
}

/**
 * État git du projet, et actions pour le versionner (ticket-061).
 *
 * Sans dépôt, le pipeline ne crée ni branche ni commit : le travail des agents
 * reste dans l'arbre, sans trace. C'est l'information la plus utile à montrer
 * avant de lancer quoi que ce soit.
 */
export default function GitLinkPanel({ project }: GitLinkPanelProps) {
  const git = useGitStatus(project?.id ?? null);
  const [repoUrl, setRepoUrl] = useState("");
  const [artifacts, setArtifacts] = useState<ArtifactModeState | null>(null);
  const [removing, setRemoving] = useState(false);

  const projectId = project?.id ?? null;

  useEffect(() => {
    if (!projectId) {
      setArtifacts(null);
      return;
    }
    let cancelled = false;
    api.git
      .artifacts(projectId)
      .then((state) => !cancelled && setArtifacts(state))
      .catch(() => !cancelled && setArtifacts(null));
    return () => {
      cancelled = true;
    };
  }, [projectId, git.status]);

  const changeMode = useCallback(
    (mode: ArtifactMode) => {
      if (!projectId) return;
      void api.git
        .setArtifacts(projectId, mode)
        .then(setArtifacts)
        .catch(() => undefined);
    },
    [projectId],
  );

  if (!project) return null;

  const status = git.status;
  const linked = status?.is_repository && status.remote_url;

  return (
    <section className="border-t border-zinc-800 px-3 py-2.5 text-xs">
      <h3 className="mb-1.5 font-medium uppercase tracking-wide text-zinc-500">
        Versionnement
      </h3>

      {git.loading && !status && <p className="text-zinc-600">Vérification…</p>}

      {status && !status.is_repository && (
        <div className="space-y-1.5">
          <p className="text-amber-400">Ce projet n'est pas versionné.</p>
          <p className="text-zinc-500">
            Sans dépôt git, un pipeline ne crée ni branche ni commit : le
            travail des agents reste dans l'arbre, sans trace.
          </p>
          {status.nested_in && (
            <p className="text-zinc-500">
              Il se trouve dans le dépôt <code>{status.nested_in}</code>, qui
              n'est pas le sien.
            </p>
          )}
          <button
            type="button"
            onClick={() => void git.init()}
            disabled={git.loading}
            className="rounded bg-zinc-700 px-2 py-1 text-zinc-100 hover:bg-zinc-600 disabled:opacity-40"
          >
            Initialiser un dépôt git
          </button>
        </div>
      )}

      {status?.is_repository && !linked && (
        <div className="space-y-1.5">
          <p className="text-zinc-400">Versionné, sans dépôt distant.</p>
          <label htmlFor="git-remote-url" className="sr-only">
            URL du dépôt GitHub
          </label>
          <input
            id="git-remote-url"
            type="text"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            placeholder="https://github.com/moi/mon-repo.git"
            className="w-full rounded bg-zinc-800 px-2 py-1 text-zinc-200 placeholder-zinc-600 outline-none focus:ring-1 focus:ring-zinc-600"
          />
          <button
            type="button"
            onClick={() => void git.link(repoUrl)}
            disabled={git.loading || repoUrl.trim().length === 0}
            className="rounded bg-zinc-700 px-2 py-1 text-zinc-100 hover:bg-zinc-600 disabled:opacity-40"
          >
            Lier à ce dépôt
          </button>
        </div>
      )}

      {linked && (
        <p className="break-all text-green-400">
          Lié à <code>{status?.remote_url}</code>
        </p>
      )}

      {artifacts && (
        <div className="mt-2 border-t border-zinc-800 pt-2">
          <p className="mb-1 text-zinc-500">
            Tickets, mémoire et ADR de ce projet
          </p>
          <div className="flex gap-1">
            {(["tracked", "local"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => changeMode(mode)}
                aria-pressed={artifacts.mode === mode}
                className={`rounded px-2 py-0.5 ${
                  artifacts.mode === mode
                    ? "bg-zinc-600 text-zinc-100"
                    : "bg-zinc-800 text-zinc-400 hover:text-zinc-200"
                }`}
              >
                {mode === "tracked" ? "dans le dépôt" : "locaux"}
              </button>
            ))}
          </div>
          {artifacts.mode === "local" && (
            <p className="mt-1 text-zinc-600">
              Exclus via <code>.git/info/exclude</code>, jamais via{" "}
              <code>.gitignore</code> — rien n'apparaît dans un diff.
            </p>
          )}
          {artifacts.mode === "local" && artifacts.already_tracked.length > 0 && (
            <p className="mt-1 text-amber-400">
              {artifacts.already_tracked.length} fichier(s) déjà suivi(s) par
              git : l'exclusion ne les en sort pas. Utilise{" "}
              <code>git rm --cached</code> si tu veux les retirer.
            </p>
          )}
        </div>
      )}

      <div className="mt-2 border-t border-zinc-800 pt-2">
        <button
          type="button"
          onClick={() => setRemoving(true)}
          className="text-zinc-500 hover:text-zinc-300"
        >
          Retirer ce projet de l'IDE…
        </button>
      </div>

      {removing && (
        <RemoveProjectModal
          project={project}
          onClose={() => setRemoving(false)}
          onRemoved={() => {
            setRemoving(false);
            // Le projet n'existe plus : la liste doit repartir du serveur.
            window.location.reload();
          }}
        />
      )}

      {git.errorMessage && (
        <div className="mt-1.5 rounded border border-amber-900/50 bg-amber-950/40 p-1.5 text-amber-300">
          <p className="break-words">{git.errorMessage}</p>
          {git.needsConfirmation && (
            <button
              type="button"
              onClick={() => void git.link(repoUrl, true)}
              className="mt-1 rounded bg-amber-800 px-2 py-0.5 text-amber-50 hover:bg-amber-700"
            >
              Lier quand même
            </button>
          )}
          <button
            type="button"
            onClick={git.clearError}
            className="mt-1 ml-2 text-amber-500 hover:text-amber-300"
          >
            Masquer
          </button>
        </div>
      )}
    </section>
  );
}
