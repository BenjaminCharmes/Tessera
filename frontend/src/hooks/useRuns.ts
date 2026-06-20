import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import type { PipelineRun } from "../types/api";

export interface UseRunsResult {
  runs: PipelineRun[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useRuns(projectId: string | null): UseRunsResult {
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!projectId) {
      setRuns([]);
      return;
    }
    setLoading(true);
    setError(null);
    api.runs
      .list(projectId)
      .then((data) => {
        setRuns(data);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Unknown error");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [projectId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { runs, loading, error, refresh };
}
