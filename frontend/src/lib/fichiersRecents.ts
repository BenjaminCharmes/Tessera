import {
  ecrireEtatPersistant,
  lireEtatPersistant,
} from "../hooks/useEtatPersistant";

/** Nombre de fichiers gardés par projet dans « Ouverts récemment » (ticket-428). */
export const MAX_RECENTS = 5;

// Une clé par projet : les fichiers d'un projet ne s'offrent jamais sous un autre.
const cle = (projectId: string): string => `fichiers-recents.${projectId}`;

function estListeDeChemins(v: unknown): v is string[] {
  return Array.isArray(v) && v.every((x) => typeof x === "string");
}

/** Les fichiers ouverts récemment dans ce projet, le plus récent d'abord. */
export function lireRecents(projectId: string): string[] {
  const liste = lireEtatPersistant<string[]>(cle(projectId), [], estListeDeChemins);
  return liste.slice(0, MAX_RECENTS);
}

/**
 * Note l'ouverture d'un fichier : il passe en tête, sans doublon, et la liste
 * est coupée à `MAX_RECENTS`. Rend la nouvelle liste.
 */
export function noterRecent(projectId: string, chemin: string): string[] {
  const liste = [chemin, ...lireRecents(projectId).filter((p) => p !== chemin)];
  const gardes = liste.slice(0, MAX_RECENTS);
  ecrireEtatPersistant(cle(projectId), gardes);
  return gardes;
}
