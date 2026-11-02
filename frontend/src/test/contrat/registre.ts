import { api } from "../../lib/api";
import { apiQuota } from "../../lib/quota";
import { statutsDuRun } from "../../lib/statutDuRun";
import { apiVentilation } from "../../lib/ventilation";

export type Verbe = "get" | "post";

/** Une fonction du client frontend et la route dont elle lit la réponse. */
export interface Appel {
  nom: string;
  objet: object;
  methode: string;
  verbe: Verbe;
  route: string;
}

const PROJET = "/api/v1/projects/{project_id}";

/**
 * Le périmètre couvert (ticket-684). Chaque entrée lie une fonction du client
 * à sa route : le garde valide ce que `mockResolvedValue` lui rend, et
 * `contrat.test.ts` confronte le type qu'elle déclare au schéma.
 */
export const APPELS: Appel[] = [
  { nom: "statutsDuRun.lire", objet: statutsDuRun, methode: "lire", verbe: "get", route: "/api/v1/runs/{run_id}" },
  { nom: "apiVentilation.parProjet", objet: apiVentilation, methode: "parProjet", verbe: "get", route: `${PROJET}/usage/breakdown` },
  { nom: "apiQuota.fenetres", objet: apiQuota, methode: "fenetres", verbe: "get", route: "/api/v1/usage/quota" },
  { nom: "api.services.list", objet: api.services, methode: "list", verbe: "get", route: `${PROJET}/services` },
  { nom: "api.services.start", objet: api.services, methode: "start", verbe: "post", route: `${PROJET}/services/start` },
  { nom: "api.services.stop", objet: api.services, methode: "stop", verbe: "post", route: `${PROJET}/services/stop` },
  { nom: "api.services.running", objet: api.services, methode: "running", verbe: "get", route: "/api/v1/services/running" },
  { nom: "api.git.cleanupPlan", objet: api.git, methode: "cleanupPlan", verbe: "get", route: `${PROJET}/branches/cleanup` },
  { nom: "api.git.cleanup", objet: api.git, methode: "cleanup", verbe: "post", route: `${PROJET}/branches/cleanup` },
];

/** Ce qui est couvert, au format de `routesDuSchema`. */
export function routesCouvertes(): string[] {
  return APPELS.map((a) => `${a.verbe.toUpperCase()} ${a.route}`).sort();
}

/** L'appel d'une fonction du client, quand le contrat la couvre. */
export function appelDe(objet: object, methode: string): Appel | undefined {
  return APPELS.find((a) => a.objet === objet && a.methode === methode);
}
