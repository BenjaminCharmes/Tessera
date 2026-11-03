import { api } from "../lib/api";
import type { ProjectOverview } from "../types/api";
import { useResource } from "./useResource";

const AUCUN: ProjectOverview[] = [];
const lire = () => api.projects.overview();
const CLE = { projet: "global", ressource: "apercu-projets" };

/**
 * La vue d'ensemble des projets, lue une fois et partagée par clé de cache :
 * chaque salle et chaque pièce du Bureau y trouve l'icône de son projet
 * (ticket-726) sans relancer la requête.
 */
export function useApercuDesProjets(): ProjectOverview[] {
  return useResource(lire, AUCUN, CLE).data;
}

/** Le projet d'un identifiant, ou `undefined` tant que la vue d'ensemble n'est pas lue. */
export function useApercuDuProjet(projectId: string): ProjectOverview | undefined {
  return useApercuDesProjets().find((p) => p.id === projectId);
}
