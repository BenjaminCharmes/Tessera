import type { AppEnCours, ServiceActif } from "../types/api";
import { post } from "./apiVerbes";
import { request } from "./http";

export const services = {
  /**
   * Les services d'un projet — ticket-137. Rien de declare dans son
   * `agents.json`, et `start` repond 409 en disant quoi ecrire.
   */
  list: (projectId: string): Promise<ServiceActif[]> =>
    request(`/projects/${projectId}/services`),
  start: (projectId: string): Promise<{ services: ServiceActif[] }> =>
    post(`/projects/${projectId}/services/start`, {}),
  stop: (projectId: string): Promise<{ arretes: number }> =>
    post(`/projects/${projectId}/services/stop`, {}),
  /** Les apps vivantes de tous les projets — ticket-416. */
  running: (): Promise<AppEnCours[]> => request("/services/running"),
  /** Arrête une app de l'inventaire courant ; 404 pour tout autre pid. */
  stopRunning: (pid: number): Promise<{ pid: number; arretes: number }> =>
    post(`/services/running/${pid}/stop`, {}),
};
