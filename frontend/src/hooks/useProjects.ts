import { api } from "../lib/api";
import { useResource } from "./useResource";
import type { Project } from "../types/api";

interface UseProjectsResult {
  projects: Project[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

const AUCUN: Project[] = [];

const listerProjets = () => api.projects.list();

export function useProjects(): UseProjectsResult {
  const { data, loading, error, refresh } = useResource(listerProjets, AUCUN);
  return { projects: data, loading, error, refresh };
}
