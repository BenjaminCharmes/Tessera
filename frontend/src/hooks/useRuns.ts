import { useMemo } from "react";
import { api } from "../lib/api";
import { useResource } from "./useResource";
import type { PipelineRun } from "../types/api";

export interface UseRunsResult {
  runs: PipelineRun[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

const AUCUN: PipelineRun[] = [];

export function useRuns(projectId: string | null): UseRunsResult {
  // Le fetcher change avec le projet : c'est ce qui invalide la réponse en
  // vol du projet quitté (ticket-123).
  const fetcher = useMemo(
    () => (projectId ? () => api.runs.list(projectId) : null),
    [projectId],
  );
  const { data, loading, error, refresh } = useResource(fetcher, AUCUN);
  return { runs: data, loading, error, refresh };
}
