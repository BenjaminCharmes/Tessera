import { listEntries, type DirEntry } from "./fs";

/** Garde-fous : un dépôt client peut compter des dizaines de milliers de fichiers. */
export const LIMITE_FICHIERS = 5000;
const PROFONDEUR_MAX = 8;
export const MAX_RESULTATS = 20;

// Dossiers générés ou vendus : les parcourir noie la recherche et coûte cher.
const IGNORES: ReadonlySet<string> = new Set([
  ".git",
  "node_modules",
  ".venv",
  "venv",
  "__pycache__",
  ".mypy_cache",
  ".pytest_cache",
  ".ruff_cache",
  "dist",
  "build",
  "target",
  ".next",
]);

async function lireDossier(chemin: string): Promise<DirEntry[]> {
  try {
    return await listEntries(chemin);
  } catch {
    // Un dossier illisible ne doit pas faire échouer toute la recherche.
    return [];
  }
}

/**
 * Liste les fichiers d'un projet, niveau par niveau, avec les mêmes appels que
 * l'arbre (`listEntries`) : la recherche ne voit que ce que l'arbre pourrait
 * montrer.
 */
export async function listerFichiers(racine: string): Promise<string[]> {
  const fichiers: string[] = [];
  let niveau = [racine];
  for (
    let profondeur = 0;
    profondeur <= PROFONDEUR_MAX && niveau.length > 0 && fichiers.length < LIMITE_FICHIERS;
    profondeur += 1
  ) {
    const lots = await Promise.all(niveau.map(lireDossier));
    const suivant: string[] = [];
    for (const entree of lots.flat()) {
      if (!entree.is_dir) fichiers.push(entree.path);
      else if (!IGNORES.has(entree.name)) suivant.push(entree.path);
    }
    niveau = suivant;
  }
  return fichiers.slice(0, LIMITE_FICHIERS);
}

const normaliser = (chemin: string): string => chemin.replace(/\\/g, "/");

/** Le chemin d'un fichier depuis la racine du projet, séparateurs en `/`. */
export function cheminRelatif(racine: string, chemin: string): string {
  const base = normaliser(racine).replace(/\/+$/, "");
  const complet = normaliser(chemin);
  return complet.startsWith(`${base}/`) ? complet.slice(base.length + 1) : complet;
}

/** Joint un chemin relatif à la racine du projet — l'inverse de `cheminRelatif`. */
export function cheminAbsolu(racine: string, relatif: string): string {
  return `${normaliser(racine).replace(/\/+$/, "")}/${relatif}`;
}

/** Les fichiers dont le chemin relatif contient la requête, sans tenir compte de la casse. */
export function filtrerFichiers(
  fichiers: string[],
  racine: string,
  requete: string,
): string[] {
  const motif = requete.trim().toLowerCase();
  if (!motif) return [];
  return fichiers
    .filter((f) => cheminRelatif(racine, f).toLowerCase().includes(motif))
    .slice(0, MAX_RESULTATS);
}
