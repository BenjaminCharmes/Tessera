import type { Project } from "../../types/api";

export interface GroupeDeProjets {
  /** `null` : les projets qui ne déclarent rien. */
  categorie: string | null;
  projets: Project[];
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
export function grouperParCategorie(projects: Project[]): GroupeDeProjets[] {
  const parCategorie = new Map<string, Project[]>();
  const sansCategorie: Project[] = [];

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

  const groupes: GroupeDeProjets[] = [...parCategorie.entries()]
    .sort(([a], [b]) => a.localeCompare(b, "fr"))
    .map(([categorie, projets]) => ({ categorie, projets }));

  if (sansCategorie.length > 0) {
    groupes.push({ categorie: null, projets: sansCategorie });
  }
  return groupes;
}
