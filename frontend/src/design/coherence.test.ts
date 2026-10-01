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
  it("n'a aucune feuille de style que personne n'importe", () => {
    // Panne vécue : les règles du Markdown rendu avaient atterri dans un
    // `styles.css` que rien n'importait. Le build passait, les tests aussi, et
    // la vue « Rendu » s'affichait sans aucun style — un mur de texte
    // indifférencié (ticket-078).
    const feuilles = readdirSync(RACINE).filter((n) => n.endsWith(".css"));
    const sources = sourcesTsx(RACINE)
      .concat(
        readdirSync(RACINE)
          .filter((n) => n.endsWith(".tsx") || n.endsWith(".ts"))
          .map((n) => join(RACINE, n)),
      )
      .map((c) => readFileSync(c, "utf-8"))
      .join("");

    const orphelines = feuilles.filter((f) => !sources.includes(f));

    expect(orphelines).toEqual([]);
  });

  it("n'utilise que les cinq familles de couleurs qui ont un rôle", () => {
    // Cinq familles d'état — zinc (neutre), red (échec), amber (attente),
    // green (succès), blue (activité) — plus `violet`, réservé à l'identité
    // et à l'interaction, en fond ou en barre uniquement (ADR-026 amendé,
    // ticket-248). Jamais un état, sinon la lecture des cinq autres se brouille.
    //
    // emerald doublait green ; orange et yellow doublaient amber ; purple
    // servait des métadonnées, qui sont neutres.
    //
    // Aucune exception déclarée : le test couvre l'ensemble des fichiers .tsx,
    // y compris ceux du ticket-282 (FilDuRun, PipelineSummary, InfoTip,
    // CreateProjectModal, ImportProjectModal, ProjectNav).
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

  it("réserve la palette de données aux graphiques", () => {
    // ADR-047 : trois teintes pour distinguer des séries, jamais un état.
    // Hors de `design/charts/`, un `data-1` se lirait comme une sixième
    // couleur d'état ; et les familles d'où elles viennent ne s'emploient pas
    // en brut, sinon la palette validée se contourne d'un nom de classe.
    const token = /(bg|text|border|ring|fill|stroke)-data-\d/;
    const brutes = ["cyan", "indigo", "pink"];
    const fautifs = FICHIERS.flatMap(({ chemin, contenu }) => [
      ...(token.test(contenu) && !chemin.startsWith("design/charts/")
        ? [chemin + " → data-*"]
        : []),
      ...brutes
        .filter((c) =>
          new RegExp("(bg|text|border|ring|fill|stroke)-" + c + "-\\d").test(contenu),
        )
        .map((c) => chemin + " → " + c),
    ]);

    expect(fautifs).toEqual([]);
  });

  it("n'écrit jamais le violet en couleur de texte", () => {
    // ADR-026 (amendé, ticket-248) : le violet s'emploie en fond ou en barre —
    // identité, sélection, action principale — jamais en couleur de texte,
    // sinon il se lit comme une sixième couleur d'état. La seule exception,
    // les liens soulignés du Markdown rendu, vit dans index.css, pas ici.
    const texteViolet = /(?:hover:)?text-violet-\d/;
    const fautifs = FICHIERS.filter(({ contenu }) =>
      texteViolet.test(contenu),
    ).map(({ chemin }) => chemin);

    expect(fautifs).toEqual([]);
  });

  it("ne sort les hex violets d'index.css que sur un lien souligné ou une barre de citation", () => {
    // Le test des classes ne voit pas les hex : les règles du Markdown rendu
    // avaient réintroduit du violet en dur. Deux emplois restent légitimes —
    // le lien, parce qu'il est souligné (l'affordance n'est pas que la
    // couleur), et la bordure de citation, qui est une barre, pas un mot.
    const hexViolets =
      /#(?:ede9fe|ddd6fe|c4b5fd|a78bfa|8b5cf6|7c3aed|6d28d9|5b21b6|4c1d95|2e1065)\b/i;
    const css = readFileSync(join(RACINE, "index.css"), "utf-8");
    const fautives = css.split("\n").filter((ligne) => {
      if (!hexViolets.test(ligne)) return false;
      const lienSouligne =
        /\ba\s*\{/.test(ligne) && ligne.includes("underline");
      const barreDeCitation =
        ligne.includes("blockquote") && ligne.includes("border-left");
      return !lienSouligne && !barreDeCitation;
    });

    expect(fautives).toEqual([]);
  });

  it("ne trace aucune icône hors de design/", () => {
    // NavRail définissait huit SVG locaux sur sa propre grille (ticket-251) :
    // le jeu d'icônes se compose à un seul endroit, `design/icons.tsx`, sinon
    // deux dessins d'une même famille divergent sans que rien ne le mesure.
    const fautifs = FICHIERS.filter(
      ({ chemin, contenu }) =>
        !chemin.startsWith("design/") && contenu.includes("<svg"),
    ).map(({ chemin }) => chemin);

    expect(fautifs).toEqual([]);
  });

  it("n'utilise aucune taille de texte en valeur arbitraire", () => {
    // `text-micro` et `text-mini` sont déclarées dans le `@theme` d'index.css :
    // une échelle nommée est un choix, `text-[10px]` est une échappatoire.
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
    // `×` (×) : le signe multiplier servait de bouton de fermeture dans
    // ChatPanel, hors des plages surveillées (ticket-251).
    const glyphes = new RegExp(
      "[\\u00D7\\u2190-\\u21FF\\u2460-\\u27BF\\u2B00-\\u2BFF\\u2588\\u25A0-\\u25FF\\u2200-\\u22FF]|[\\u{1F000}-\\u{1FAFF}]",
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
