import { type Grille, R, type Sprite, cuire, sprite } from "./grille";

/*
 * Plantes, machine à café, meuble bas, bibliothèque, étagère (atelier,
 * `sprites/mobilier.js` et `mur.js`, ticket-727) : du mobilier fixe, grille ×2.
 * Aucun ne porte d'état (ADR-058).
 */

const LIVRES = [R("livre1"), R("livre2"), R("livre3")] as const;
const livre = (t: 1 | 2 | 3) => LIVRES[t - 1];

/** Des touffes de feuillage : disques ombrés, du fond vers l'avant. */
export function feuillage(g: Grille, fam: string, touffes: readonly (readonly [number, number, number])[]): void {
  for (const [cx, cy, r] of touffes) g.disc(cx, cy, r, fam);
}

/** Un pot qui s'affine : rebord éclairé, terre, flanc droit dans l'ombre. */
export function pot(g: Grille, fam: string, x: number, y: number, w: number, h: number, terre: string | null = "terre.b"): void {
  const Pt = R(fam);
  g.rect(x, y, w, 2, Pt.b);
  g.rect(x, y, w, 1, Pt.hi);
  if (terre) g.rect(x + 1, y, w - 2, 1, terre);
  g.rect(x, y + 2, w, 1, Pt.d);
  for (let j = 0; j < h; j++) {
    const i = 1 + Math.floor(j / 3);
    g.rect(x + i, y + 3 + j, w - 2 * i, 1, Pt.b);
    g.px(x + w - i - 1, y + 3 + j, Pt.s);
    g.px(x + w - i - 2, y + 3 + j, Pt.s);
    g.px(x + i + 1, y + 3 + j, Pt.hi);
  }
}

export type EspeceDePlante = "pot" | "cactus" | "ficus";

/** Une plante : en pot 16 × 20, cactus fleuri 16 × 20, ficus 16 × 32. */
export function plante(esp: EspeceDePlante): Sprite {
  if (esp === "pot") {
    const s = sprite(16, 20);
    const g = s.calque();
    g.rect(7, 5, 2, 7, "plante.d");
    feuillage(g, "plante", [[4, 6, 3], [11, 5, 3], [8, 3, 2.6], [3.5, 10, 2.2], [12.5, 9.5, 2.2], [8, 8, 2.4]]);
    pot(g, "pot", 2, 12, 12, 6);
    return cuire(s);
  }
  if (esp === "cactus") {
    const s = sprite(16, 20);
    const g = s.calque();
    const K = R("cactus");
    const tronc = (x: number, y: number, w: number, h: number) => {
      g.rect(x, y, w, h, K.b);
      g.rect(x, y, 1, h, K.hi);
      g.rect(x + w - 1, y, 1, h, K.s);
      if (w > 3) g.rect(x + 2, y + 1, 1, h - 1, K.s);
      g.rect(x, y, w, 1, K.hi);
      g.clr(x, y);
      g.clr(x + w - 1, y);
    };
    tronc(6, 2, 4, 12);
    tronc(2, 5, 3, 5);
    g.rect(2, 9, 5, 2, K.b);
    g.rect(2, 10, 5, 1, K.s);
    tronc(11, 3, 3, 6);
    g.rect(9, 7, 5, 2, K.b);
    g.rect(9, 8, 5, 1, K.s);
    for (const [x, y] of [[7, 4], [9, 6], [7, 9], [9, 11], [3, 7], [12, 5], [6, 12]] as const) g.px(x, y, "epine.b");
    g.rect(7, 0, 2, 2, "fleur.b");
    g.px(6, 1, "fleur.s");
    g.px(9, 1, "fleur.s");
    g.px(7, 0, "fleur.hi");
    pot(g, "pot-clair", 3, 13, 10, 5);
    return cuire(s);
  }
  const s = sprite(16, 32);
  const g = s.calque();
  g.rect(7, 16, 2, 7, "bois.s");
  g.px(7, 18, "bois.b");
  g.px(6, 19, "bois.s");
  feuillage(g, "plante", [[8, 6, 6], [4, 10, 4], [12, 10, 4], [8, 13, 4.2], [6, 3, 3], [11, 4, 3]]);
  pot(g, "pot", 2, 22, 12, 8);
  return cuire(s);
}

/** La machine à café, 24 × 32 : afficheur, trois boutons, buse, tasse pleine. Aucun voyant. */
export function machineACafe(): Sprite {
  const s = sprite(24, 32);
  const g = s.calque();
  const M = R("machine");
  g.rect(2, 0, 20, 28, M.b);
  g.rect(2, 0, 20, 2, M.hi);
  g.rect(2, 0, 2, 28, M.hi);
  g.rect(19, 2, 3, 26, M.s);
  g.rect(6, 3, 12, 6, M.d);
  g.rect(7, 4, 10, 4, "cadre.d");
  g.rect(8, 5, 4, 1, M.s);
  for (const x of [7, 11, 15]) {
    g.rect(x, 10, 2, 2, M.d);
    g.px(x, 10, M.hi);
  }
  g.rect(6, 14, 12, 11, M.d);
  g.rect(10, 14, 4, 3, "metal.hi");
  g.rect(11, 17, 2, 1, "metal.s");
  g.rect(9, 19, 5, 5, "tasse.b");
  g.rect(9, 19, 5, 1, "tasse.hi");
  g.rect(10, 19, 3, 1, "cafe.b");
  g.rect(13, 20, 1, 4, "tasse.s");
  g.rect(14, 20, 1, 2, "tasse.s");
  g.rect(5, 24, 14, 2, M.s);
  for (let x = 6; x < 18; x += 2) g.px(x, 24, M.d);
  g.rect(0, 28, 24, 4, M.s);
  g.rect(0, 28, 24, 1, M.b);
  g.rect(0, 31, 24, 1, M.d);
  return cuire(s);
}

/** Le meuble bas de la machine à café, 32 × 16 : plateau, un tiroir, une porte. */
export function meubleBas(): Sprite {
  const s = sprite(32, 16);
  const g = s.calque();
  const W = R("bois");
  const M = R("metal");
  g.rect(0, 0, 32, 3, W.b);
  g.rect(0, 0, 32, 1, W.hi);
  g.rect(0, 2, 32, 1, W.s);
  g.rect(1, 3, 30, 13, W.s);
  g.rect(1, 3, 30, 1, W.d);
  g.rect(3, 5, 26, 3, W.b);
  g.rect(3, 5, 26, 1, W.hi);
  g.rect(14, 6, 4, 1, M.hi);
  g.rect(3, 9, 26, 6, W.b);
  g.rect(3, 9, 1, 6, W.hi);
  g.rect(28, 9, 1, 6, W.s);
  g.rect(25, 11, 1, 2, M.hi);
  g.rect(1, 15, 30, 1, W.d);
  return cuire(s);
}

/** Un rang de la bibliothèque : un livre debout [x, w, h, teinte], couché ["L", x, w, h, teinte], une plante ["P", x]. */
type Rangee = readonly (
  | readonly [number, number, number, 1 | 2 | 3]
  | readonly ["L", number, number, number, 1 | 2 | 3]
  | readonly ["P", number]
)[];
const RANGS: readonly Rangee[] = [
  [[3, 3, 8, 1], [6, 2, 7, 2], [8, 3, 8, 3], [11, 2, 6, 1], [14, 3, 8, 2], [17, 3, 7, 3], ["L", 21, 7, 2, 1], [24, 3, 8, 3]],
  [[3, 2, 6, 3], [5, 3, 8, 2], [8, 3, 8, 1], ["L", 12, 8, 2, 3], ["P", 22], [25, 3, 7, 2]],
  [[3, 3, 8, 2], [6, 2, 6, 1], [8, 3, 8, 3], [11, 3, 7, 2], ["L", 15, 6, 2, 1], ["L", 15, 4, 2, 2], [22, 2, 8, 3], [24, 3, 7, 1]],
];

/** La bibliothèque, 32 × 36 : reliures avec dos et bandeau, livres couchés, une petite plante. */
export function bibliotheque(): Sprite {
  const s = sprite(32, 36);
  const g = s.calque();
  const W = R("bois");
  g.rect(0, 0, 32, 36, W.s);
  g.rect(0, 0, 32, 2, W.hi);
  g.rect(0, 0, 2, 36, W.b);
  g.rect(0, 0, 1, 36, W.hi);
  g.rect(30, 0, 2, 36, W.b);
  g.rect(31, 1, 1, 35, W.s);
  g.rect(30, 0, 2, 1, W.hi);
  RANGS.forEach((livres, i) => {
    const haut = 2 + i * 11;
    const base = haut + 9;
    g.rect(2, haut, 28, 9, W.d);
    for (const b of livres) {
      if (b[0] === "L") {
        const [, x, w, h, t] = b;
        const B = livre(t);
        g.rect(x, base - h, w, h, B.b);
        g.rect(x, base - h, w, 1, B.hi);
        g.rect(x + 1, base - 1, w - 2, 1, B.s);
      } else if (b[0] === "P") {
        const x = b[1];
        g.rect(x, base - 3, 3, 3, "pot.b");
        g.px(x + 2, base - 2, "pot.s");
        feuillage(g, "plante", [[x + 1.5, base - 5, 1.8]]);
      } else {
        const [x, w, h, t] = b;
        const B = livre(t);
        g.rect(x, base - h, w, h, B.b);
        g.rect(x, base - h, 1, h, B.hi);
        if (w > 2) g.rect(x + w - 1, base - h, 1, h, B.s);
        g.rect(x, base - h + 2, w, 1, B.d);
      }
    }
    g.rect(2, base, 28, 1, W.hi);
    g.rect(2, base + 1, 28, 1, W.b);
  });
  return cuire(s);
}

/** L'étagère, 32 × 20 : planche sur deux équerres, une plante en pot, deux livres debout, un couché. */
export function etagere(): Sprite {
  const s = sprite(32, 20);
  const g = s.calque();
  const W = R("bois");
  g.rect(6, 5, 2, 2, "plante.d");
  feuillage(g, "plante", [[4.5, 4, 2.2], [9.5, 3.5, 2.2], [7, 2, 2], [7, 5, 2]]);
  pot(g, "pot", 3, 6, 8, 3);
  const debout = (x: number, y: number, w: number, h: number, B: ReturnType<typeof R>) => {
    g.rect(x, y, w, h, B.b);
    g.rect(x, y, 1, h, B.hi);
    g.rect(x + w - 1, y, 1, h, B.s);
    g.rect(x, y + 2, w, 1, B.d);
    g.rect(x, y + h - 3, w, 1, B.d);
  };
  debout(16, 4, 4, 8, livre(1));
  debout(20, 6, 6, 6, livre(2));
  g.rect(26, 9, 5, 3, "livre3.b");
  g.rect(26, 9, 5, 1, "livre3.hi");
  g.rect(26, 10, 4, 1, "tasse.b");
  g.rect(30, 10, 1, 2, "livre3.s");
  g.rect(0, 12, 32, 4, W.b);
  g.rect(0, 12, 32, 1, W.hi);
  g.rect(0, 15, 32, 1, W.s);
  g.rect(31, 13, 1, 3, W.s);
  for (const [x, y] of [[5, 13], [6, 13], [18, 14], [19, 14], [27, 13]] as const) g.px(x, y, W.s);
  for (const x0 of [2, 26]) {
    for (let j = 0; j < 4; j++) {
      g.rect(x0, 16 + j, 4 - j, 1, W.s);
      g.px(x0, 16 + j, W.b);
    }
  }
  return cuire(s);
}
