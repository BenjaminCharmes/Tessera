import type { AppEnCours } from "../types/api";

/** Au-delà, un arrêt ou un lancement est déclaré échoué — ticket-424. */
export const DELAI_ATTENTE_MS = 30_000;

/** Les opérations en cours : clé de l'opération → heure du clic. */
export type Attentes = Record<string, number>;

export const cleArret = (pid: number): string => `arret:${pid}`;
export const cleLancement = (projectId: string): string => `lancement:${projectId}`;

function estResolue(cle: string, apps: AppEnCours[]): boolean {
  const coupure = cle.indexOf(":");
  const genre = cle.slice(0, coupure);
  const valeur = cle.slice(coupure + 1);
  if (genre === "arret") return !apps.some((app) => String(app.pid) === valeur);
  return apps.some((app) => app.project_id === valeur);
}

export interface TriAttentes {
  restantes: Attentes;
  /** Les clés abandonnées faute de réponse dans le délai. */
  expirees: string[];
}

/**
 * Sépare ce qui est résolu (le pid a disparu, le projet est revenu), ce qui a
 * expiré, et ce qui attend encore. Pure : le hook décide quoi en faire.
 */
export function trierAttentes(
  attentes: Attentes,
  apps: AppEnCours[],
  now: number,
): TriAttentes {
  const restantes: Attentes = {};
  const expirees: string[] = [];
  for (const [cle, depuis] of Object.entries(attentes)) {
    if (estResolue(cle, apps)) continue;
    if (now - depuis >= DELAI_ATTENTE_MS) expirees.push(cle);
    else restantes[cle] = depuis;
  }
  return { restantes, expirees };
}

/** Ajoute des clés à `attentes`, toutes datées de `now`. */
export function ajouter(attentes: Attentes, cles: string[], now: number): Attentes {
  const suite = { ...attentes };
  for (const cle of cles) suite[cle] = now;
  return suite;
}

/** Retire des clés de `attentes`. */
export function retirer(attentes: Attentes, cles: string[]): Attentes {
  const suite = { ...attentes };
  for (const cle of cles) delete suite[cle];
  return suite;
}
