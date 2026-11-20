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
  /**
   * Le conteneur de la fonction tel que le fichier de test le voit : le vrai quand
   * il importe le client, celui d'un `vi.mock` quand il le remplace. Le garde y
   * retrouve les mocks que `vi.mocked` lui rend. `undefined` : la fabrique du
   * mock ne l'expose pas.
   */
  charger: () => Promise<object | undefined>;
}

const PROJET = "/api/v1/projects/{project_id}";

// Import dynamique : au moment de l'appel, le module est celui que le fichier de test voit.
const dansServices = async (): Promise<object | undefined> => (await import("../../lib/api")).api.services;
const dansGit = async (): Promise<object | undefined> => (await import("../../lib/api")).api.git;

/**
 * Le périmètre couvert (ticket-684). Chaque entrée lie une fonction du client
 * à sa route : le garde valide ce que `mockResolvedValue` lui rend, et
 * `contrat.test.ts` confronte le type qu'elle déclare au schéma.
 */
export const APPELS: Appel[] = [
  { nom: "statutsDuRun.lire", objet: statutsDuRun, methode: "lire", verbe: "get", route: "/api/v1/runs/{run_id}", charger: async () => (await import("../../lib/statutDuRun")).statutsDuRun },
  { nom: "apiVentilation.parProjet", objet: apiVentilation, methode: "parProjet", verbe: "get", route: `${PROJET}/usage/breakdown`, charger: async () => (await import("../../lib/ventilation")).apiVentilation },
  { nom: "apiQuota.fenetres", objet: apiQuota, methode: "fenetres", verbe: "get", route: "/api/v1/usage/quota", charger: async () => (await import("../../lib/quota")).apiQuota },
  { nom: "api.services.list", objet: api.services, methode: "list", verbe: "get", route: `${PROJET}/services`, charger: dansServices },
  { nom: "api.services.start", objet: api.services, methode: "start", verbe: "post", route: `${PROJET}/services/start`, charger: dansServices },
  { nom: "api.services.stop", objet: api.services, methode: "stop", verbe: "post", route: `${PROJET}/services/stop`, charger: dansServices },
  { nom: "api.services.running", objet: api.services, methode: "running", verbe: "get", route: "/api/v1/services/running", charger: dansServices },
  { nom: "api.git.cleanupPlan", objet: api.git, methode: "cleanupPlan", verbe: "get", route: `${PROJET}/branches/cleanup`, charger: dansGit },
  { nom: "api.git.cleanup", objet: api.git, methode: "cleanup", verbe: "post", route: `${PROJET}/branches/cleanup`, charger: dansGit },
];

/** Ce qui est couvert, au format de `routesDuSchema`. */
export function routesCouvertes(): string[] {
  return APPELS.map((a) => `${a.verbe.toUpperCase()} ${a.route}`).sort();
}

/** L'appel d'une fonction du client, quand le contrat la couvre. */
export function appelDe(objet: object, methode: string): Appel | undefined {
  return APPELS.find((a) => a.objet === objet && a.methode === methode);
}
