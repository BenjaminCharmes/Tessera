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
    for (const sprite of ["Personnage", "Poste", "Ecran", "Bulle", "Pastille", "Plante", "Porte", "Vapeur"]) {
      expect(noms).toContain(`${sprite}.tsx`);
    }
  });

  it("keeps room furniture on --sprite-* tokens, still and without a status hue", () => {
    for (const nom of ["MachineACafe.tsx", "TableDeReunion.tsx", "Porte.tsx"]) {
      const contenu = SPRITES.find((s) => s.nom === nom)?.contenu ?? "";
      expect(contenu, nom).toContain("--sprite-");
      expect(contenu, nom).not.toMatch(/anim-|animation|green/);
      expect(contenu, nom).not.toMatch(/\b(?:fill|stroke|bg|text)-(?:zinc|red|amber|blue|violet)-\d/);
    }
  });

  it("draws the plant as fixed furniture from --sprite-* tokens, with no animation class", () => {
    const plante = SPRITES.find((s) => s.nom === "Plante.tsx")?.contenu ?? "";

    expect(plante).not.toMatch(/anim-/);
    for (const jeton of ["plante", "plante-ombre", "pot", "sol", "sol-joint"]) {
      expect(CSS).toMatch(new RegExp(`--sprite-${jeton}:`));
    }
    expect(plante).toContain("--sprite-plante");
    expect(plante).toContain("--sprite-pot");
  });

  it("draws the whiteboard from --sprite-* tokens, still, with state tones kept in tons.ts", () => {
    const tableau = SPRITES.find((s) => s.nom === "TableauBlanc.tsx")?.contenu ?? "";
    const tons = SPRITES.find((s) => s.nom === "tons.ts")?.contenu ?? "";

    expect(tableau).toContain("--sprite-tableau");
    expect(tableau).not.toMatch(/anim-|animation/);
    for (const jeton of ["tableau", "tableau-cadre", "tableau-case"]) {
      expect(CSS).toMatch(new RegExp(`--sprite-${jeton}:`));
    }
    expect(tons).toMatch(/passe:\s*"fill-green-\d{3}"/);
    expect(tons).toMatch(/echoue:\s*"fill-red-\d{3}"/);
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
  const keyframes = [...CSS.matchAll(/@keyframes\s+(tape|lueur|flotte|vapeur|chute|gyro)\b/g)].map(
    (m) => m[1] ?? "",
  );

  it("declares the six animations", () => {
    expect(keyframes.sort()).toEqual(["chute", "flotte", "gyro", "lueur", "tape", "vapeur"]);
  });

  it("animates only transform and opacity", () => {
    const proprietes = blocs(CSS, /@keyframes\s+(?:tape|lueur|flotte|vapeur|chute|gyro)\b/).flatMap((corps) =>
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

  it("cuts the confetti fall and the beacon blink under prefers-reduced-motion", () => {
    const [reduit] = blocs(CSS, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);

    expect(reduit).toMatch(/[.]anim-chute\b[^{]*[{][^}]*animation:\s*none/);
    expect(reduit).toMatch(/[.]anim-gyro\b[^{]*[{][^}]*animation:\s*none/);
    expect(CSS).toMatch(/[.]anim-chute\s*[{]\s*animation:\s*chute\s/);
    expect(CSS).toMatch(/[.]anim-gyro\s*[{]\s*animation:\s*gyro\s/);
  });

  it("plays the fall on the confetti and the blink on the beacon, with --sprite-* tones", () => {
    const confettis = SPRITES.find((x) => x.nom === "Confettis.tsx")?.contenu ?? "";
    const gyrophare = SPRITES.find((x) => x.nom === "Gyrophare.tsx")?.contenu ?? "";

    expect(confettis).toContain("anim-chute");
    expect(gyrophare).toContain("anim-gyro");
    for (const jeton of ["confetti-1", "confetti-5", "gyrophare", "gyrophare-socle"]) {
      expect(CSS).toMatch(new RegExp(`--sprite-${jeton}:`));
    }
  });

  it("draws the steam from its own sprite and token, not from the machine", () => {
    const vapeur = SPRITES.find((x) => x.nom === "Vapeur.tsx")?.contenu ?? "";

    expect(vapeur).toContain("anim-vapeur");
    expect(vapeur).toContain("--sprite-vapeur");
    expect(CSS).toMatch(/--sprite-vapeur:/);
  });

  it("walks the agents with a transition that reduced motion removes", () => {
    const regle = CSS.match(/[.]marche\s*[{]([^}]*)[}]/)?.[1] ?? "";
    expect(regle).toMatch(/transition:\s*transform/);

    const [reduit] = blocs(CSS, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);
    expect(reduit).toMatch(/[.]marche\s*[{]\s*transition:\s*none/);
  });

  it("animates the walk with transform and opacity only", () => {
    const regle = CSS.match(/[.]marche\s*[{]([^}]*)[}]/)?.[1] ?? "";
    const valeur = regle.match(/transition:\s*([^;]+);/)?.[1] ?? "";
    const proprietes = valeur.split(",").map((p) => p.trim().split(/\s+/)[0]);

    expect(proprietes.length).toBeGreaterThan(0);
    expect(proprietes.filter((p) => p !== "transform" && p !== "opacity")).toEqual([]);
  });
});
