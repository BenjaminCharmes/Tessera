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
const MOTEUR = sourcesDe(join(SRC, "lib", "bureau", "sprites"));
/** Le mobilier des pièces et des salles : du moteur, fixe, sans état (ADR-058, ticket-727). */
const MOBILIER = [
  "MachineACafe.tsx", "TableDeReunion.tsx", "Porte.tsx", "Plante.tsx", "Horloge.tsx", "Etagere.tsx",
  "Cadre.tsx", "Corbeille.tsx", "Bibliotheque.tsx", "Canape.tsx", "Frigo.tsx", "Classeur.tsx",
  "Chaise.tsx", "Imprimante.tsx", "Dossier.tsx", "Interrupteur.tsx",
];
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
  it("has a source file per sprite, and the engine that draws them", () => {
    const noms = SPRITES.map((s) => s.nom);
    for (const sprite of ["AgentDebout", "Poste", "EcranScenes", "Bulle", "Pastille", "Plante", "Porte", "Vapeur", "SpriteSvg", "DefsDuBureau", "Tuile"]) {
      expect(noms).toContain(`${sprite}.tsx`);
    }
    for (const module of ["grille", "jeton", "symboles", "ambiance", "mobilier", "mur", "tableau", "objets", "serveurs", "ecrans", "communs", "poste", "debout"]) {
      expect(MOTEUR.map((s) => s.nom)).toContain(`${module}.ts`);
    }
  });

  it("draws the room furniture from the engine, still and without a status hue", () => {
    for (const nom of MOBILIER) {
      const contenu = SPRITES.find((s) => s.nom === nom)?.contenu ?? "";
      expect(contenu, nom).toContain("lib/bureau/sprites/");
      expect(contenu, nom).toContain("SpriteSvg");
      expect(contenu, nom).not.toMatch(/anim-|animation|transition/);
      expect(contenu, nom).not.toMatch(/\b(?:fill|stroke|bg|text)-(?:zinc|red|amber|green|blue|violet)-\d/);
    }
    // Les modules du mobilier ne posent ni état ni animation : ADR-058.
    for (const nom of ["mobilier.ts", "communs.ts", "ambiance.ts"]) {
      const contenu = MOTEUR.find((s) => s.nom === nom)?.contenu ?? "";
      expect(contenu, nom).not.toMatch(/anim-|etat-|\bE\(/);
    }
  });

  it("draws the whiteboard boxes in state tones only: grey, green when passed, red when failed", () => {
    const tableau = MOTEUR.find((s) => s.nom === "tableau.ts")?.contenu ?? "";

    expect(tableau).toMatch(/attente:\s*"attente"/);
    expect(tableau).toMatch(/passe:\s*"fait"/);
    expect(tableau).toMatch(/echoue:\s*"blocage"/);
    expect(tableau).not.toMatch(/anim-/);
  });

  it("draws the sprites with crisp pixels and no transition", () => {
    for (const nom of ["SpriteSvg.tsx", "DefsDuBureau.tsx", "Tuile.tsx"]) {
      expect(SPRITES.find((s) => s.nom === nom)?.contenu, nom).toContain('shapeRendering="crispEdges"');
    }
    // Une transition CSS, pas un événement de transition (`onTransitionEnd`).
    const tous = [...SPRITES, ...VUE, ...MOTEUR].filter((s) => /(?<![A-Za-z])transition(?![A-Za-z])/.test(s.contenu));
    expect(tous.map((s) => s.nom)).toEqual([]);
  });

  it("writes no raw colour in the sprite engine either", () => {
    const fautifs = MOTEUR.filter(({ contenu }) => /#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(|\boklch\(/.test(contenu)).map((s) => s.nom);
    expect(fautifs).toEqual([]);
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

  it("reads skin, hair and role tones through the generic slots of a shared drawing", () => {
    const jeton = MOTEUR.find((s) => s.nom === "jeton.ts")?.contenu ?? "";
    for (const famille of ["peau", "cheveux", "haut"]) expect(jeton).toContain(`"${famille}"`);
    expect(jeton).toContain("--sp-");
  });

  it("declares the sprite tokens in a static theme so var() finds them", () => {
    const [theme] = blocs(CSS, /@theme\s+static/);
    expect(theme).toBeDefined();
    expect(theme).toContain("--sprite-halo-coeur");
  });
});

describe("Bureau animations", () => {
  const NOMS = "tape|lueur|flotte|vapeur|chute|gyro|defile|scintille|clignote|trame-4|trame-6|trame-8";
  const keyframes = [...CSS.matchAll(new RegExp(`@keyframes\\s+(${NOMS})(?![\\w-])`, "g"))].map((m) => m[1] ?? "");

  it("declares the twelve animations of the Bureau", () => {
    expect(keyframes.sort()).toEqual([
      "chute",
      "clignote",
      "defile",
      "flotte",
      "gyro",
      "lueur",
      "scintille",
      "tape",
      "trame-4",
      "trame-6",
      "trame-8",
      "vapeur",
    ]);
  });

  it("animates only transform and opacity", () => {
    const proprietes = blocs(CSS, new RegExp(`@keyframes\\s+(?:${NOMS})(?![\\w-])`)).flatMap((corps) =>
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
      const classe = CSS.match(new RegExp(`([.][a-z0-9-]+)[ ]*[{][ ]*animation(?:-name)?:[ ]*${nom}[ ;]`))?.[1];
      expect(classe, `a class plays ${nom}`).toBeDefined();
      // Une image par image se coupe par sa classe commune (`.anim-trame`), qui remet l'animation à zéro.
      expect(reduit).toContain((classe ?? "").replace(/-\d$/, ""));
    }
  });

  it("cuts the confetti fall and the beacon blink under prefers-reduced-motion", () => {
    const [reduit] = blocs(CSS, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);

    expect(reduit).toMatch(/[.]anim-chute\b[^{]*[{][^}]*animation:\s*none/);
    expect(reduit).toMatch(/[.]anim-gyro\b[^{]*[{][^}]*animation:\s*none/);
    expect(CSS).toMatch(/[.]anim-chute\s*[{]\s*animation:\s*chute\s/);
    expect(CSS).toMatch(/[.]anim-gyro\s*[{]\s*animation:\s*gyro\s/);
  });

  it("plays the fall on the confetti and the blink on the beacon dome, in the blocked tone", () => {
    const confettis = SPRITES.find((x) => x.nom === "Confettis.tsx")?.contenu ?? "";
    const objets = MOTEUR.find((x) => x.nom === "objets.ts")?.contenu ?? "";

    expect(confettis).toContain('className="anim-chute');
    expect(objets).toContain('s.calque("anim-gyro")');
    expect(objets).toContain('E("blocage")');
  });

  it("draws the steam from its own sprite and token, not from the machine", () => {
    const objets = MOTEUR.find((x) => x.nom === "objets.ts")?.contenu ?? "";
    const mobilier = MOTEUR.find((x) => x.nom === "mobilier.ts")?.contenu ?? "";

    expect(objets).toContain("anim-vapeur");
    expect(objets).toContain("vapeur.hi");
    expect(mobilier).not.toContain("vapeur");
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
