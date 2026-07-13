import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import type { ProjectUsage } from "../types/api";

export interface UseUsageResult {
  usage: ProjectUsage | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useUsage(projectId: string | null): UseUsageResult {
  const [usage, setUsage] = useState<ProjectUsage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!projectId) {
      setUsage(null);
      return;
    }
    setLoading(true);
    setError(null);
    api.usage
      .get(projectId)
      .then((data) => {
        setUsage(data);
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

  return { usage, loading, error, refresh };
}
