import { api } from "../lib/api";
import { useResource } from "./useResource";
import type { AgentInfo } from "../types/api";

export interface UseAgentsResult {
  agents: AgentInfo[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

const AUCUN: AgentInfo[] = [];

// Hors du composant : le registre d'agents n'a pas de paramètre, donc une
// seule requête pour toute la vie du hook.
const listerAgents = () => api.agents.list();

export function useAgents(): UseAgentsResult {
  const { data, loading, error, refresh } = useResource(listerAgents, AUCUN);
  return { agents: data, loading, error, refresh };
}
