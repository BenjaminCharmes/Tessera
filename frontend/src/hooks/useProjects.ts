import { useEffect } from "react";
import { api } from "../lib/api";
import { useResource } from "./useResource";
import type { Project } from "../types/api";

const EVENEMENT_PROJETS = "tessera:projets-modifies";

/**
 * Dit à toutes les listes de projets de se relire — ticket-399.
 *
 * Chaque `useProjects()` tient sa propre copie : changer une catégorie depuis
 * la vue Projets laissait la barre latérale sur l'ancien rangement. Un
 * évènement de la fenêtre suffit, sans état global (ADR-013).
 */
export function notifierProjetsModifies(): void {
  window.dispatchEvent(new Event(EVENEMENT_PROJETS));
}

interface UseProjectsResult {
  projects: Project[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

const AUCUN: Project[] = [];

/**
 * Délai avant de relire une liste en échec — ticket-621.
 *
 * Le frontend est prêt avant le backend au démarrage : une seule lecture
 * ratée laissait la liste vide jusqu'au rechargement, et le clic sur un
 * projet ne sélectionnait rien, sans un mot.
 */
export const DELAI_DE_RELECTURE_MS = 3000;

const listerProjets = () => api.projects.list();

export function useProjects(): UseProjectsResult {
  const { data, loading, error, refresh } = useResource(listerProjets, AUCUN);
  useEffect(() => {
    window.addEventListener(EVENEMENT_PROJETS, refresh);
    return () => window.removeEventListener(EVENEMENT_PROJETS, refresh);
  }, [refresh]);
  useEffect(() => {
    if (error === null) return;
    const minuteur = window.setTimeout(refresh, DELAI_DE_RELECTURE_MS);
    return () => window.clearTimeout(minuteur);
  }, [error, refresh]);
  return { projects: data, loading, error, refresh };
}
