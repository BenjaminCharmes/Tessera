/**
 * Découper un diff unifié en fichiers et en lignes typées — ticket-075.
 *
 * Le diff arrivait d'un bloc dans Monaco : tous les fichiers concaténés, les
 * ajouts et les retraits noyés dans la même couleur, et rien pour naviguer.
 * Sur un dépôt où un run touche cinq fichiers dont deux Markdown de plusieurs
 * centaines de lignes, c'est illisible.
 *
 * On découpe donc ici, une fois, et l'affichage se contente de peindre.
 */
export type TypeDeLigne = "ajout" | "retrait" | "contexte" | "hunk" | "entete";

export interface LigneDiff {
  type: TypeDeLigne;
  texte: string;
}

export interface FichierDiff {
  chemin: string;
  ajouts: number;
  retraits: number;
  lignes: LigneDiff[];
}

function typeDeLigne(ligne: string): TypeDeLigne {
  if (ligne.startsWith("@@")) return "hunk";
  if (ligne.startsWith("+++") || ligne.startsWith("---")) return "entete";
  if (ligne.startsWith("+")) return "ajout";
  if (ligne.startsWith("-")) return "retrait";
  return "contexte";
}

/** Le chemin d'un fichier depuis sa ligne `diff --git a/x b/x`. */
function cheminDepuisEntete(ligne: string): string {
  const m = /^diff --git a\/(.+?) b\/(.+)$/.exec(ligne);
  return m ? m[2]! : ligne.replace("diff --git ", "");
}

export function decouperDiff(diff: string): FichierDiff[] {
  if (!diff.trim()) return [];

  const fichiers: FichierDiff[] = [];
  let courant: FichierDiff | null = null;

  for (const ligne of diff.split("\n")) {
    if (ligne.startsWith("diff --git ")) {
      courant = {
        chemin: cheminDepuisEntete(ligne),
        ajouts: 0,
        retraits: 0,
        lignes: [],
      };
      fichiers.push(courant);
      continue;
    }
    if (courant === null) continue;

    // `index …` et les modes ne disent rien d'utile à la lecture.
    if (ligne.startsWith("index ") || ligne.startsWith("new file mode")) continue;

    const type = typeDeLigne(ligne);
    if (type === "entete") continue;
    if (type === "ajout") courant.ajouts += 1;
    if (type === "retrait") courant.retraits += 1;
    courant.lignes.push({ type, texte: ligne });
  }

  return fichiers;
}
