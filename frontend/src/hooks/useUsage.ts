import { useMemo } from "react";
import { api } from "../lib/api";
import { useResource } from "./useResource";
import type { ProjectUsage } from "../types/api";

export interface UseUsageResult {
  usage: ProjectUsage | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useUsage(projectId: string | null): UseUsageResult {
  const fetcher = useMemo(
    () => (projectId ? () => api.usage.get(projectId) : null),
    [projectId],
  );
  const { data, loading, error, refresh } = useResource<ProjectUsage | null>(
    fetcher,
    null,
  );
  return { usage: data, loading, error, refresh };
}
