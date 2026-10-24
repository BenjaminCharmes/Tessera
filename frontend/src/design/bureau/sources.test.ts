import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

/**
 * Tests de source du Bureau — ticket-562, ADR-058.
 *
 * Ce que le rendu ne montre pas, la source le dit : une couleur brute ou une
 * propriété animée coûteuse ne casse aucun test de composant, et se paie à
 * l'écran sur dix pièces.
 */
const SRC = join(__dirname, "..", "..");
const FAMILLES_PERMISES = ["zinc", "red", "amber", "green", "blue"];

function sourcesDe(dossier: string): { nom: string; contenu: string }[] {
  return readdirSync(dossier)
    .filter((nom) => /\.tsx?$/.test(nom) && !/\.test\.tsx?$/.test(nom))
    .map((nom) => ({ nom, contenu: readFileSync(join(dossier, nom), "utf-8") }));
}

const SPRITES = sourcesDe(__dirname);
const VUE = sourcesDe(join(SRC, "components", "BureauView"));
const CSS = readFileSync(join(SRC, "index.css"), "utf-8");

/** Le corps d'un bloc `@xxx { ... }` dont l'en-tête commence par `entete`. */
function blocs(css: string, entete: RegExp): string[] {
  const corps: string[] = [];
  for (const m of css.matchAll(new RegExp(entete.source + "[^{]*[{]", "g"))) {
    let profondeur = 1;
    let i = (m.index ?? 0) + m[0].length;
    const debut = i;
    while (profondeur > 0 && i < css.length) {
      if (css[i] === "{") profondeur += 1;
      if (css[i] === "}") profondeur -= 1;
      i += 1;
    }
    corps.push(css.slice(debut, i - 1));
  }
  return corps;
}

describe("sprites sources", () => {
  it("has a source file per sprite", () => {
    const noms = SPRITES.map((s) => s.nom);
    for (const sprite of ["Personnage", "Poste", "Ecran", "Bulle", "Pastille"]) {
      expect(noms).toContain(`${sprite}.tsx`);
    }
  });

  it("writes no raw colour in design/bureau", () => {
    const fautifs = SPRITES.filter(({ contenu }) =>
      /#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(|\boklch\(/.test(contenu),
    ).map((s) => s.nom);

    expect(fautifs).toEqual([]);
  });

  it("uses only the state families of Tailwind in design/bureau", () => {
    const familles = SPRITES.flatMap(({ nom, contenu }) =>
      [...contenu.matchAll(/\b(?:fill|stroke|bg|text|border|ring|outline)-([a-z]+)-\d{2,3}/g)].map(
        (m) => ({ nom, famille: m[1] ?? "" }),
      ),
    );

    expect(familles.length).toBeGreaterThan(0);
    expect(familles.filter((f) => !FAMILLES_PERMISES.includes(f.famille))).toEqual([]);
  });

  it("reads skin, hair and folder tones from --sprite-* tokens defined in index.css", () => {
    for (const jeton of ["peau", "cheveux", "dossier"]) {
      expect(CSS).toMatch(new RegExp(`--sprite-${jeton}:`));
    }
    const lus = SPRITES.map((s) => s.contenu).join("");
    expect(lus).toContain("--sprite-peau");
    expect(lus).toContain("--sprite-cheveux");
  });

  it("declares the sprite tokens in a static theme so var() finds them", () => {
    const [theme] = blocs(CSS, /@theme\s+static/);
    expect(theme).toBeDefined();
    expect(theme).toContain("--sprite-peau");
  });

  it("draws the sprites with crisp pixel rectangles and no transition", () => {
    const poste = SPRITES.find((s) => s.nom === "Poste.tsx")?.contenu ?? "";
    expect(poste).toContain('shapeRendering="crispEdges"');
    const tous = [...SPRITES, ...VUE].filter((s) => /transition/i.test(s.contenu));
    expect(tous.map((s) => s.nom)).toEqual([]);
  });
});

describe("Bureau animations", () => {
  const keyframes = [...CSS.matchAll(/@keyframes\s+(tape|lueur|flotte)\b/g)].map((m) => m[1] ?? "");

  it("declares the three animations", () => {
    expect(keyframes.sort()).toEqual(["flotte", "lueur", "tape"]);
  });

  it("animates only transform and opacity", () => {
    const proprietes = blocs(CSS, /@keyframes\s+(?:tape|lueur|flotte)\b/).flatMap((corps) =>
      [...corps.matchAll(/([a-z-]+)\s*:/g)].map((m) => m[1] ?? ""),
    );

    expect(proprietes.length).toBeGreaterThan(0);
    expect(proprietes.filter((p) => p !== "transform" && p !== "opacity")).toEqual([]);
  });

  it("switches every animation off under prefers-reduced-motion", () => {
    const [reduit] = blocs(CSS, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);
    expect(reduit).toBeDefined();
    expect(reduit).toMatch(/animation:\s*none/);
    for (const nom of keyframes) {
      const classe = CSS.match(new RegExp(`([.][a-z-]+)[ ]*[{][ ]*animation:[ ]*${nom}[ ]`))?.[1];
      expect(classe, `a class plays ${nom}`).toBeDefined();
      expect(reduit).toContain(classe ?? "");
    }
  });
});
