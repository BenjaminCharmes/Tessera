import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import type { AgentInfo } from "../types/api";

export interface UseAgentsResult {
  agents: AgentInfo[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useAgents(): UseAgentsResult {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    api.agents
      .list()
      .then((data) => {
        setAgents(data);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Unknown error");
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { agents, loading, error, refresh };
}
