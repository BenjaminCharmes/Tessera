import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import type { GitStatus } from "../types/api";

interface GitStatusState {
  status: GitStatus | null;
  loading: boolean;
  errorMessage: string | null;
  /** Le dépôt distant a un historique : la liaison doit être confirmée. */
  needsConfirmation: boolean;
}

export interface UseGitStatusResult extends GitStatusState {
  init: () => Promise<void>;
  link: (repoUrl: string, confirmed?: boolean) => Promise<void>;
  clearError: () => void;
}

const INITIAL: GitStatusState = {
  status: null,
  loading: false,
  errorMessage: null,
  needsConfirmation: false,
};

function message(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

/**
 * État git d'un projet, et actions pour le versionner (ticket-061).
 *
 * Un projet créé de zéro ou importé en mode `copy` n'a aucun dépôt : le
 * pipeline ne peut alors ni brancher ni committer, et le travail des agents
 * reste dans l'arbre sans trace.
 */
export function useGitStatus(projectId: string | null): UseGitStatusResult {
  const [state, setState] = useState<GitStatusState>(INITIAL);

  const refresh = useCallback(async () => {
    if (!projectId) {
      setState(INITIAL);
      return;
    }
    setState((s) => ({ ...s, loading: true }));
    try {
      const status = await api.git.status(projectId);
      setState({ ...INITIAL, status });
    } catch (err: unknown) {
      setState({ ...INITIAL, errorMessage: message(err) });
    }
  }, [projectId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const init = useCallback(async () => {
    if (!projectId) return;
    setState((s) => ({ ...s, loading: true, errorMessage: null }));
    try {
      setState({ ...INITIAL, status: await api.git.init(projectId) });
    } catch (err: unknown) {
      setState((s) => ({ ...s, loading: false, errorMessage: message(err) }));
    }
  }, [projectId]);

  const link = useCallback(
    async (repoUrl: string, confirmed = false) => {
      if (!projectId) return;
      setState((s) => ({
        ...s,
        loading: true,
        errorMessage: null,
        needsConfirmation: false,
      }));
      try {
        setState({ ...INITIAL, status: await api.git.link(projectId, repoUrl, confirmed) });
      } catch (err: unknown) {
        const text = message(err);
        // Un 409 signale un dépôt distant non vide : ce n'est pas une erreur,
        // c'est une décision que l'utilisateur seul peut prendre.
        setState((s) => ({
          ...s,
          loading: false,
          errorMessage: text,
          needsConfirmation: text.includes("409"),
        }));
      }
    },
    [projectId],
  );

  const clearError = useCallback(() => {
    setState((s) => ({ ...s, errorMessage: null, needsConfirmation: false }));
  }, []);

  return { ...state, init, link, clearError };
}
