import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

/**
 * Verrou de cohérence visuelle — ticket-067.
 *
 * L'UI a dérivé vers huit familles de couleurs, trois tailles de texte en dur
 * et des glyphes empruntés à autant de jeux, parce que chaque feature a choisi
 * au moment où elle était écrite. Rien ne mesurait la dérive, donc personne ne
 * la voyait avant qu'elle ne saute aux yeux à l'écran.
 *
 * Ces tests sont la mesure. Ils échouent sur la première réintroduction, pas
 * six mois plus tard.
 */
const RACINE = join(__dirname, "..");

function sourcesTsx(dossier: string): string[] {
  return readdirSync(dossier).flatMap((nom) => {
    const chemin = join(dossier, nom);
    if (statSync(chemin).isDirectory()) return sourcesTsx(chemin);
    if (!chemin.endsWith(".tsx") || chemin.endsWith(".test.tsx")) return [];
    return [chemin];
  });
}

const FICHIERS = sourcesTsx(RACINE).map((chemin) => ({
  chemin: chemin.slice(RACINE.length + 1).replace(/\\/g, "/"),
  contenu: readFileSync(chemin, "utf-8"),
}));

describe("cohérence visuelle", () => {
  it("n'utilise que les cinq familles de couleurs qui ont un rôle", () => {
    // Cinq familles d'état — zinc (neutre), red (échec), amber (attente),
    // green (succès), blue (activité) — plus `violet`, réservé à l'identité
    // et au repérage : titre de région, élément actif du rail, nom du projet.
    // Jamais un état, sinon la lecture des cinq autres se brouille.
    //
    // emerald doublait green ; orange et yellow doublaient amber ; purple
    // servait des métadonnées, qui sont neutres.
    const bannies = ["emerald", "purple", "orange", "yellow"];
    const fautifs = FICHIERS.flatMap(({ chemin, contenu }) =>
      bannies
        .filter((c) =>
          new RegExp("(bg|text|border|ring)-" + c + "-\\d").test(contenu),
        )
        .map((c) => chemin + " → " + c),
    );

    expect(fautifs).toEqual([]);
  });

  it("n'utilise aucune taille de texte en valeur arbitraire", () => {
    // `text-micro` et `text-mini` sont déclarées dans tailwind.config : une
    // échelle nommée est un choix, `text-micro` est une échappatoire.
    const arbitraire = new RegExp("text-\\[\\d+px\\]");
    const fautifs = FICHIERS.filter(({ contenu }) =>
      arbitraire.test(contenu),
    ).map(({ chemin }) => chemin);

    expect(fautifs).toEqual([]);
  });

  it("n'utilise aucun glyphe ni emoji comme affordance", () => {
    // Les icônes viennent de `design/icons.tsx`, tracées sur une seule grille.
    // Un glyphe collé dans du JSX ne se contrôle ni en taille, ni en trait, ni
    // en alignement, et son rendu dépend de la police du système.
    const glyphes = new RegExp(
      "[\\u2190-\\u21FF\\u2460-\\u27BF\\u2B00-\\u2BFF\\u2588\\u25A0-\\u25FF\\u2200-\\u22FF]|[\\u{1F000}-\\u{1FAFF}]",
      "u",
    );
    const fautifs = FICHIERS.filter(({ chemin, contenu }) => {
      if (chemin === "design/icons.tsx") return false;
      return contenu
        .split("\n")
        .some((ligne) => {
          // Un glyphe cité dans un commentaire documente ce qu'on a retiré :
          // c'est de la prose, pas une affordance.
          const debut = ligne.trimStart();
          const commentaire =
            debut.startsWith("//") ||
            debut.startsWith("*") ||
            debut.startsWith("/*") ||
            debut.startsWith("{/*");
          return !commentaire && glyphes.test(ligne);
        });
    }).map(({ chemin }) => chemin);

    expect(fautifs).toEqual([]);
  });
});
