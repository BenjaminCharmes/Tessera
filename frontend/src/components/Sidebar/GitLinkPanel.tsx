import BranchCleanup from "./BranchCleanup";
import { useCallback, useMemo, useState } from "react";
import { api } from "../../lib/api";
import { useGitStatus } from "../../hooks/useGitStatus";
import { lienDuDepot } from "../../lib/lienDuDepot";
import { useResource } from "../../hooks/useResource";
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

  const projectId = project?.id ?? null;

  // Le mode des artefacts se relit avec le statut git : un `init` ou un lien
  // change ce que l'exclusion peut faire. Le statut fait donc partie de la clé
  // de la requête, même si la requête ne le lit pas (ticket-123).
  const statut = git.status;
  const fetcher = useMemo(
    () =>
      projectId
        ? () => {
            void statut;
            return api.git.artifacts(projectId);
          }
        : null,
    [projectId, statut],
  );
  const charge = useResource<ArtifactModeState | null>(fetcher, null);
  /** Ce que le dernier changement de mode a rendu, prioritaire sur la lecture. */
  const [modifie, setModifie] = useState<{
    fetcher: () => Promise<ArtifactModeState>;
    state: ArtifactModeState;
  } | null>(null);
  const artifacts =
    fetcher && modifie?.fetcher === fetcher ? modifie.state : charge.data;

  const changeMode = useCallback(
    (mode: ArtifactMode) => {
      if (!projectId || !fetcher) return;
      void api.git
        .setArtifacts(projectId, mode)
        .then((state) => setModifie({ fetcher, state }))
        .catch(() => undefined);
    },
    [projectId, fetcher],
  );

  if (!project) return null;

  const status = git.status;
  const linked = status?.is_repository && status.remote_url;
  // Une adresse SSH ou un chemin local n'ouvre rien : le texte reste alors
  // du texte, plutôt qu'un lien qui mènerait ailleurs (ticket-184).
  const lien = lienDuDepot(status?.remote_url);

  return (
    <section className="border-t border-zinc-800 px-3 py-2.5 text-xs">
      <h3 className="mb-1.5 font-medium uppercase tracking-wide text-zinc-500">
        Versionnement
      </h3>

      {git.loading && !status && <p className="text-zinc-600">Vérification…</p>}

      {/* Travailler dans le dépôt qui le contient est le mode normal d'un
          projet en `git_root: ancestor` (ADR-028), pas une anomalie. L'écran
          l'annonçait comme non versionné et proposait d'imbriquer un dépôt
          dans celui de Tessera — ce qu'ADR-024 existe pour empêcher
          (ticket-171). */}
      {status?.uses_parent_repository && (
        <p className="text-zinc-400">
          Ce projet travaille dans le dépôt qui le contient,{" "}
          <code className="break-all">{status.nested_in}</code> — c'est ce que
          déclare son <code>git_root</code>.
        </p>
      )}

      {status && !status.is_repository && !status.uses_parent_repository && (
        <div className="space-y-1.5">
          <p className="text-amber-400">Ce projet n'est pas versionné.</p>
          <p className="text-zinc-500">
            Sans dépôt git, un pipeline ne crée ni branche ni commit : le
            travail des agents reste dans l'arbre, sans trace.
          </p>
          {status.nested_in && (
            <p className="text-zinc-500">
              Il se trouve dans le dépôt{" "}
              <code className="break-all">{status.nested_in}</code>, qui n'est
              pas le sien.
            </p>
          )}
          <button
            type="button"
            onClick={() => void git.init()}
            disabled={git.loading}
            className="rounded-sm bg-zinc-700 px-2 py-1 text-zinc-100 hover:bg-zinc-600 disabled:opacity-40"
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
            className="w-full rounded-sm bg-zinc-800 px-2 py-1 text-zinc-200 placeholder-zinc-600 outline-hidden focus:ring-1 focus:ring-zinc-600"
          />
          <button
            type="button"
            onClick={() => void git.link(repoUrl)}
            disabled={git.loading || repoUrl.trim().length === 0}
            className="rounded-sm bg-zinc-700 px-2 py-1 text-zinc-100 hover:bg-zinc-600 disabled:opacity-40"
          >
            Lier à ce dépôt
          </button>
        </div>
      )}

      {linked && (
        <p className="break-all text-green-400">
          Lié à{" "}
          {lien ? (
            <a
              href={lien}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 hover:text-green-300"
              title="Ouvrir le dépôt"
            >
              <code>{status?.remote_url}</code>
            </a>
          ) : (
            <code>{status?.remote_url}</code>
          )}
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
          {artifacts.mode === "local" &&
            artifacts.already_tracked.length > 0 && (
              <p className="mt-1 text-amber-400">
                {artifacts.already_tracked.length} fichier(s) déjà suivi(s) par
                git : l'exclusion ne les en sort pas. Utilise{" "}
                <code>git rm --cached</code> si tu veux les retirer.
              </p>
            )}
        </div>
      )}

      {git.errorMessage && (
        <div className="mt-1.5 rounded-sm border border-amber-900/50 bg-amber-950/40 p-1.5 text-amber-300">
          <p className="wrap-break-word">{git.errorMessage}</p>
          {git.needsConfirmation && (
            <button
              type="button"
              onClick={() => void git.link(repoUrl, true)}
              className="mt-1 rounded-sm bg-amber-800 px-2 py-0.5 text-amber-50 hover:bg-amber-700"
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
          <BranchCleanup projectId={project.id} />
        </div>
      )}
    </section>
  );
}
