import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";

/**
 * Contraste du favicon — ticket-101.
 *
 * Le pavement du favicon original s'affichait à 1.00:1 contre la barre
 * d'onglets sombre (contraste nul) et à 1.07:1 contre la barre claire. Les
 * couleurs avaient été validées contre le fond de la page, pas contre la barre
 * d'onglets où le favicon est réellement posé.
 *
 * Chaque couleur portant une forme doit tenir seule sur les quatre fonds
 * réels, jeu clair et jeu sombre évalués indépendamment — OS et navigateur
 * peuvent diverger, la media query n'en distingue que deux des quatre
 * combinaisons possibles.
 */

const RACINE = join(__dirname, "..", "..");
const FAVICON = readFileSync(join(RACINE, "public", "favicon.svg"), "utf-8");

/** Quatre fonds de référence : barres d'onglets et pages, clair et sombre. */
const FONDS: Record<string, string> = {
  "onglet sombre Chrome (#35363a)": "#35363a",
  "page sombre Chrome (#202124)": "#202124",
  "onglet clair Chrome (#dee1e6)": "#dee1e6",
  "blanc (#ffffff)": "#ffffff",
};

function hexToSrgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [
    parseInt(h.slice(0, 2), 16) / 255,
    parseInt(h.slice(2, 4), 16) / 255,
    parseInt(h.slice(4, 6), 16) / 255,
  ];
}

function linearise(c: number): number {
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

function luminance(hex: string): number {
  const [r, g, b] = hexToSrgb(hex).map(linearise) as [
    number,
    number,
    number,
  ];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contraste(hex1: string, hex2: string): number {
  const l1 = luminance(hex1);
  const l2 = luminance(hex2);
  const [clair, sombre] = l1 > l2 ? [l1, l2] : [l2, l1];
  return (clair + 0.05) / (sombre + 0.05);
}

/**
 * Extrait les couleurs hexadécimales du bloc `<style>` du SVG.
 *
 * Renvoie deux listes :
 * - `clair` : couleurs hors media query (thème OS clair)
 * - `sombre` : couleurs dans `@media (prefers-color-scheme: dark)`
 */
/** Retire les commentaires CSS, qui citent des couleurs sans les peindre. */
function sansCommentaires(css: string): string {
  return css.replace(/\/\*[\s\S]*?\*\//g, "");
}

/**
 * Sépare le bloc `@media (prefers-color-scheme: dark)` du reste du CSS.
 *
 * L'appariement se fait en comptant les accolades, pas par une expression
 * régulière : `[\s\S]*?\}` s'arrête à la première fermante, c'est-à-dire à la
 * fin de la première règle du bloc. Les suivantes retombaient alors dans le
 * jeu clair et y étaient mesurées contre les mauvais fonds — invisible tant
 * que le bloc sombre ne portait qu'une seule règle.
 */
function decoupeMediaSombre(css: string): { bloc: string; reste: string } {
  const entete = css.match(
    /@media\s*\([^)]*prefers-color-scheme:\s*dark[^)]*\)\s*\{/,
  );
  if (!entete || entete.index === undefined) return { bloc: "", reste: css };

  const debut = entete.index + entete[0].length;
  let profondeur = 1;
  let i = debut;
  for (; i < css.length && profondeur > 0; i++) {
    if (css[i] === "{") profondeur++;
    else if (css[i] === "}") profondeur--;
  }

  return {
    bloc: css.slice(debut, i - 1),
    reste: css.slice(0, entete.index) + css.slice(i),
  };
}

function extractCouleurs(svg: string): {
  clair: string[];
  sombre: string[];
} {
  const styleMatch = svg.match(/<style>([\s\S]*?)<\/style>/);
  if (!styleMatch) return { clair: [], sombre: [] };

  const css = styleMatch[1];
  const { bloc: darkCss, reste: clairCss } = decoupeMediaSombre(css);

  // Seules les déclarations qui peignent comptent. Une extraction qui balaie
  // tout le CSS ramasse aussi les hex cités dans les commentaires — dont les
  // fonds de référence, qu'elle compare alors à eux-mêmes : 1.00:1, un échec
  // qui ne désigne aucune couleur réellement dessinée.
  const peinture = /(?:fill|stroke)\s*:\s*(#[0-9a-fA-F]{6})\b/g;
  const couleursDe = (css: string): string[] =>
    [...sansCommentaires(css).matchAll(peinture)].map((m) => m[1]);

  const clairCouleurs = couleursDe(clairCss);
  const sombreCouleurs = couleursDe(darkCss);

  return { clair: clairCouleurs, sombre: sombreCouleurs };
}

const { clair, sombre } = extractCouleurs(FAVICON);

describe("contraste du favicon", () => {
  it("les deux jeux de couleurs sont définis dans le SVG", () => {
    expect(clair.length, "aucune couleur dans le thème clair").toBeGreaterThan(
      0,
    );
    expect(
      sombre.length,
      "aucune couleur dans le thème sombre (@media dark)",
    ).toBeGreaterThan(0);
  });

  it("le jeu clair passe 2.5:1 sur les quatre fonds de référence", () => {
    for (const couleur of clair) {
      for (const [nom, fond] of Object.entries(FONDS)) {
        const ratio = contraste(couleur, fond);
        expect(
          ratio,
          `${couleur} (jeu clair) sur ${nom} : ${ratio.toFixed(2)}:1 < 2.5`,
        ).toBeGreaterThanOrEqual(2.5);
      }
    }
  });

  it("le jeu sombre passe 2.5:1 sur les quatre fonds de référence", () => {
    for (const couleur of sombre) {
      for (const [nom, fond] of Object.entries(FONDS)) {
        const ratio = contraste(couleur, fond);
        expect(
          ratio,
          `${couleur} (jeu sombre) sur ${nom} : ${ratio.toFixed(2)}:1 < 2.5`,
        ).toBeGreaterThanOrEqual(2.5);
      }
    }
  });
});

/**
 * La forme, et pas seulement la couleur.
 *
 * Le contraste seul se satisfait d'un carré violet uni : c'est ce qu'a produit
 * le premier passage, et rien ne l'a signalé parce que rien ne le mesurait.
 * Or une tessera est la tuile d'une mosaïque — sans pavement autour d'elle,
 * rien ne la détache, et la marque ne dit plus de quoi elle parle.
 *
 * Le jour est ce qui porte le détachement : un vide géométrique se lit quel
 * que soit le fond, là où un écart de couleur entre tuile et pavement est
 * plafonné à 1.31:1 dès que les deux doivent rester lisibles partout.
 */
describe("structure de la marque", () => {
  it("garde un pavement autour de la tuile", () => {
    const rects = [...FAVICON.matchAll(/<rect\b/g)].length;
    expect(
      rects,
      "le favicon ne porte qu'une forme : c'est un carré, pas une tesselle détachée",
    ).toBeGreaterThan(2);
  });

  it("détache la tuile par un jour, pas par un écart de couleur", () => {
    expect(
      FAVICON,
      "aucun masque : sans jour autour d'elle, la tuile se fond dans le pavement",
    ).toMatch(/<mask\b/);
  });
});
