import type { Physique, Tenue } from "../physique";
import { type Grille, R, type Sprite, cuire, imageParImage, sprite } from "./grille";
import { type Expression, tete, torseDetails } from "./poste";

/*
 * L'agent debout, grille 24 × 40 (atelier, `sprites/personnages.js`, ticket-727) :
 * tasse à la main, mains vides, bras levés, ou la copie annotée qu'il rend. Quatre
 * images de marche (`PAS`) remplacent la glissade d'un bloc quand il se déplace.
 */

/** Une image de la marche : jambe levée (1 gauche, -1 droite), rebond, balancement des bras. */
export interface Pas {
  jambe: -1 | 0 | 1;
  rebond: 0 | 1;
  bras: -1 | 0 | 1;
}

/** Le cycle de marche, quatre images. */
export const PAS: readonly Pas[] = [
  { jambe: 0, rebond: 0, bras: 0 },
  { jambe: 1, rebond: 1, bras: 1 },
  { jambe: 0, rebond: 0, bras: 0 },
  { jambe: -1, rebond: 1, bras: -1 },
];

/** Ce que tiennent ses mains. */
export type Mains = "tasse" | "vides" | "levees" | "feuille";

export interface OptionsDebout {
  physique: Physique;
  tenue: Tenue;
  expression: Expression;
  mains: Mains;
  pas?: Pas;
}

/** Dessine l'agent debout dans `g`. */
function dessiner(g: Grille, { physique: ph, tenue, expression, mains, pas = PAS[0] as Pas }: OptionsDebout): void {
  const T = R(`haut-${tenue.haut}`);
  const K = R(`peau${ph.peau}`);
  const { rebond: b, bras: sw } = pas;
  const la = pas.jambe === 1 ? 2 : 0;
  const lb = pas.jambe === -1 ? 2 : 0;
  if (ph.jupe) {
    g.rect(5, 32 + b, 2, 6 - la - b, K.b);
    g.rect(13, 32 + b, 2, 6 - lb - b, K.s);
    g.rect(4, 38 - la, 4, 2, "chaussure.b");
    g.rect(12, 38 - lb, 4, 2, "chaussure.b");
    g.rect(2, 25 + b, 16, 7, T.s);
    g.rect(2, 31 + b, 16, 1, T.d);
    g.rect(14, 26 + b, 4, 5, T.d);
  } else {
    const Pn = R("pantalon");
    for (const [x, l] of [[4, la], [12, lb]] as const) {
      g.rect(x, 26 + b, 4, 12 - l - b, Pn.b);
      g.rect(x + 3, 26 + b, 1, 12 - l - b, Pn.s);
    }
    for (const [x, l] of [[3, la], [12, lb]] as const) {
      g.rect(x, 38 - l, 5, 2, "chaussure.b");
      g.rect(x, 38 - l, 5, 1, "chaussure.hi");
    }
    g.rect(2, 25 + b, 16, 1, Pn.d);
  }
  tete(g, 4, 3 + b, ph, expression);
  g.rect(8, 12 + b, 4, 1, K.s);
  g.rect(3, 13 + b, 14, 12, T.b);
  g.rect(2, 14 + b, 16, 11, T.b);
  g.rect(14, 14 + b, 4, 11, T.s);
  g.rect(3, 14 + b, 3, 1, T.hi);
  torseDetails(g, tenue, 5, 13 + b);
  if (mains === "levees") {
    for (const x of [0, 18]) {
      g.rect(x, 4, 2, 10, T.s);
      g.rect(x, 2, 2, 2, K.b);
    }
    return;
  }
  g.rect(0, 14 + b + sw, 2, 10, T.s);
  g.rect(0, 14 + b + sw, 1, 9, T.d);
  g.rect(0, 24 + b + sw, 2, 2, K.b);
  if (mains === "tasse") {
    g.rect(18, 14 + b, 2, 5, T.s);
    g.rect(19, 19 + b, 3, 2, K.b);
    g.rect(19, 15 + b, 3, 4, "tasse.b");
    g.rect(19, 15 + b, 3, 1, "tasse.hi");
    g.px(20, 15 + b, "cafe.b");
    g.rect(22, 16 + b, 1, 2, "tasse.s");
    g.rect(21, 16 + b, 1, 3, "tasse.s");
  } else if (mains === "feuille") {
    // Le bras tendu qui rend la copie : une feuille, deux corrections au feutre rouge.
    g.rect(18, 12 + b, 2, 8, T.s);
    g.rect(20, 6 + b, 6, 10, "papier.b");
    g.rect(20, 6 + b, 6, 1, "papier.hi");
    g.rect(25, 7 + b, 1, 9, "papier.s");
    g.rect(21, 9 + b, 3, 1, "livre1.b");
    g.rect(21, 12 + b, 4, 1, "livre1.b");
    g.rect(19, 14 + b, 2, 2, K.b);
  } else {
    g.rect(18, 14 + b - sw, 2, 10, T.s);
    g.rect(18, 24 + b - sw, 2, 2, K.b);
  }
}

/** L'agent debout, immobile. */
export function debout(o: OptionsDebout): Sprite {
  const s = sprite(24, 40);
  dessiner(s.calque(), o);
  return cuire(s);
}

/**
 * L'agent qui marche : les quatre images de `PAS`, chacune cuite à part puis posée
 * sur son calque, jouées image par image (`anim-trame-4`). Sous mouvement réduit,
 * seule la première reste : il se tient droit.
 */
export function marche(o: Omit<OptionsDebout, "pas">): Sprite {
  const calques = PAS.map((pas, i) => {
    const image = debout({ ...o, pas }).calques[0];
    return { g: image?.g ?? sprite(24, 40).calque(), classe: "anim-trame anim-trame-4", style: imageParImage(i, PAS.length, 0.64) };
  });
  return { w: 24, h: 40, calques };
}
