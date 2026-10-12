import { useCallback, useMemo, useSyncExternalStore } from "react";

/**
 * Les catégories de projets repliées — ticket-400.
 *
 * Partagé par la barre latérale et la vue « Projets » : les deux lisent la même
 * clé de `localStorage` et se préviennent quand l'une écrit, pour qu'une
 * catégorie repliée d'un côté le soit de l'autre sans rechargement.
 *
 * Chaque accès au stockage est enveloppé. Stockage illisible : tout est
 * déplié. Stockage non inscriptible : le pli vit le temps de l'onglet, dans
 * `repliEnMemoire`, plutôt que de rendre le bouton muet.
 */
const CLE = "tessera.categories-repliees";

/** Clé des projets sans catégorie, qui n'ont pas de nom à mémoriser. */
export const SANS_CATEGORIE = "__sans-categorie__";

const ecouteurs = new Set<() => void>();
let repliEnMemoire = "[]";

function lireBrut(): string {
  try {
    return window.localStorage.getItem(CLE) ?? "[]";
  } catch {
    return repliEnMemoire;
  }
}

function ecrireBrut(brut: string): void {
  try {
    window.localStorage.setItem(CLE, brut);
    repliEnMemoire = "[]";
  } catch {
    repliEnMemoire = brut;
  }
  ecouteurs.forEach((ecouteur) => ecouteur());
}

function abonner(rappel: () => void): () => void {
  ecouteurs.add(rappel);
  window.addEventListener("storage", rappel);
  return () => {
    ecouteurs.delete(rappel);
    window.removeEventListener("storage", rappel);
  };
}

function analyser(brut: string): ReadonlySet<string> {
  try {
    const valeur: unknown = JSON.parse(brut);
    if (!Array.isArray(valeur)) return new Set();
    return new Set(valeur.filter((v): v is string => typeof v === "string"));
  } catch {
    return new Set();
  }
}

interface CategoriesRepliees {
  /** `categorie` : le nom du groupe, `null` pour les projets sans catégorie. */
  estRepliee: (categorie: string | null) => boolean;
  basculer: (categorie: string | null) => void;
}

export function useCategoriesRepliees(): CategoriesRepliees {
  const brut = useSyncExternalStore(abonner, lireBrut);
  const repliees = useMemo(() => analyser(brut), [brut]);

  const estRepliee = useCallback(
    (categorie: string | null) => repliees.has(categorie ?? SANS_CATEGORIE),
    [repliees],
  );

  const basculer = useCallback((categorie: string | null) => {
    // On relit le stockage au moment du clic : l'autre vue a pu écrire entre-temps.
    const courantes = new Set(analyser(lireBrut()));
    const cle = categorie ?? SANS_CATEGORIE;
    if (!courantes.delete(cle)) courantes.add(cle);
    ecrireBrut(JSON.stringify([...courantes]));
  }, []);

  return { estRepliee, basculer };
}
