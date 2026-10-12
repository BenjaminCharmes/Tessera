import type { Project } from "../../types/api";

/** Tout ce qui porte une catégorie se range : `Project`, ou sa vue d'ensemble (ticket-399). */
type AvecCategorie = { category?: string | null };

export interface GroupeDeProjets<T extends AvecCategorie = Project> {
  /** `null` : les projets qui ne déclarent rien. */
  categorie: string | null;
  projets: T[];
}

/**
 * Range les projets par catégorie déclarée — ticket-175.
 *
 * Neuf projets dans une liste plate, dépôts clients et bancs d'essai mêlés :
 * c'est là qu'on choisit sur quoi lancer un pipeline, et deux noms voisins
 * suffisent à se tromper de dépôt.
 *
 * Les groupes nommés viennent d'abord, dans l'ordre alphabétique — un ordre
 * stable vaut mieux qu'un ordre d'apparition, qui change quand on ajoute un
 * projet. Ceux qui ne déclarent rien ferment la marche : le défaut range
 * ailleurs, il ne cache jamais.
 */
export function grouperParCategorie<T extends AvecCategorie>(
  projects: T[],
): GroupeDeProjets<T>[] {
  const parCategorie = new Map<string, T[]>();
  const sansCategorie: T[] = [];

  for (const projet of projects) {
    const categorie = projet.category?.trim();
    if (!categorie) {
      sansCategorie.push(projet);
      continue;
    }
    const groupe = parCategorie.get(categorie);
    if (groupe) groupe.push(projet);
    else parCategorie.set(categorie, [projet]);
  }

  const groupes: GroupeDeProjets<T>[] = [...parCategorie.entries()]
    .sort(([a], [b]) => a.localeCompare(b, "fr"))
    .map(([categorie, projets]) => ({ categorie, projets }));

  if (sansCategorie.length > 0) {
    groupes.push({ categorie: null, projets: sansCategorie });
  }
  return groupes;
}
