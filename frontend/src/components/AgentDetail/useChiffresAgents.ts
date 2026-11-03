import { useMemo } from "react";
import { api } from "../../lib/api";
import { useResource } from "../../hooks/useResource";
import type { BreakdownLine, UsageStats } from "../../types/api";

const AUCUNE: BreakdownLine[] = [];

export interface ChiffresAgents {
  lignes: BreakdownLine[];
  loading: boolean;
  error: string | null;
}

/** Une ligne par rôle (`per_agent`) sur 30 jours, pour le projet donné. */
export function useChiffresAgents(projectId: string | null): ChiffresAgents {
  const fetcher = useMemo(
    () => (projectId ? () => api.usage.stats(30, projectId) : null),
    [projectId],
  );
  const { data, loading, error } = useResource<UsageStats | null>(fetcher, null);
  return { lignes: data?.per_agent ?? AUCUNE, loading, error };
}
