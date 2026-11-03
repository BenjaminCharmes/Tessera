import type { Physique, Tenue } from "../physique";
import { type Grille, R, type Sprite, cuire, sprite } from "./grille";
import { tete } from "./poste";

/*
 * Les salles communes (atelier, `sprites/communs.js`, ticket-727) : canapé, frigo,
 * classeur, table de réunion, chaise, bureau en bois. Du mobilier fixe (ADR-058) ;
 * la figure du bureau (directeur, recruteuse) ne s'y assoit que si elle est là.
 */

type Tons = ReturnType<typeof R>;

/** Un coussin rembourré : dessus éclairé, flanc droit et dessous dans l'ombre, coins arrondis. */
function coussin(g: Grille, K: Tons, x: number, y: number, w: number, h: number, bouton = true): void {
  g.rect(x, y, w, h, K.b);
  g.rect(x, y, w, 1, K.hi);
  g.rect(x, y, 1, h - 1, K.hi);
  g.rect(x + w - 1, y + 1, 1, h - 1, K.s);
  g.rect(x + 1, y + h - 1, w - 1, 1, K.s);
  g.clr(x, y);
  g.clr(x + w - 1, y);
  if (bouton) g.px(x + (w >> 1), y + (h >> 1), K.d);
}

/** Le canapé, 48 × 20 : trois coussins capitonnés, deux d'assise, accoudoirs, un coussin moutarde. */
export function canape(): Sprite {
  const s = sprite(48, 20);
  const g = s.calque();
  const K = R("canape");
  const W = R("bois");
  g.rect(4, 0, 40, 11, K.d);
  for (const x of [5, 18, 31]) coussin(g, K, x, 1, 12, 9);
  g.rect(6, 10, 36, 6, K.s);
  g.rect(6, 16, 36, 2, K.d);
  for (const x of [6, 24]) {
    g.rect(x, 10, 18, 2, K.hi);
    g.rect(x, 12, 18, 4, K.b);
    g.rect(x, 15, 18, 1, K.s);
    g.px(x, 10, K.b);
  }
  g.rect(23, 10, 1, 6, K.d);
  g.rect(41, 11, 1, 5, K.s);
  const k = s.calque();
  const Ks = R("coussin");
  coussin(k, Ks, 8, 4, 8, 7, false);
  k.px(9, 5, Ks.hi);
  k.line(10, 7, 13, 7, Ks.s);
  const a = s.calque();
  for (const x of [0, 42]) {
    a.rect(x, 6, 6, 12, K.b);
    a.rect(x, 6, 6, 2, K.hi);
    a.rect(x, 6, 1, 11, K.hi);
    a.rect(x + 5, 8, 1, 10, K.s);
    a.rect(x + 1, 8, 5, 1, K.s);
    a.rect(x, 17, 6, 1, K.d);
    a.clr(x, 6);
    a.clr(x + 5, 6);
  }
  for (const x of [2, 44]) {
    a.rect(x, 18, 2, 2, W.s);
    a.px(x, 18, W.b);
  }
  return cuire(s);
}

/** Le réfrigérateur, 20 × 36 : deux portes en relief, poignées, grille, un post-it sous un aimant. */
export function frigo(): Sprite {
  const s = sprite(20, 36);
  const g = s.calque();
  const F = R("frigo");
  const M = R("metal");
  g.rect(0, 0, 20, 36, F.s);
  g.rect(0, 0, 20, 1, F.b);
  g.rect(0, 0, 1, 34, F.b);
  for (const [y, h] of [[2, 10], [14, 19]] as const) {
    g.rect(2, y, 16, h, F.b);
    g.rect(2, y, 16, 1, F.hi);
    g.rect(2, y, 2, h - 1, F.hi);
    g.rect(17, y + 1, 1, h - 1, F.s);
    g.rect(3, y + h - 1, 15, 1, F.s);
  }
  g.rect(1, 12, 18, 2, F.d);
  for (const [y, h] of [[4, 5], [16, 7]] as const) {
    g.rect(14, y, 2, h, M.b);
    g.rect(14, y, 1, h, M.hi);
    g.rect(15, y + 1, 1, h - 1, M.s);
    g.px(16, y + 1, F.s);
    g.px(16, y + h - 1, F.s);
  }
  g.rect(1, 33, 18, 3, F.d);
  for (let x = 4; x < 16; x += 2) g.px(x, 34, F.s);
  const n = s.calque();
  const Y = R("postit");
  n.rect(5, 18, 6, 6, Y.b);
  n.rect(5, 18, 6, 1, Y.hi);
  n.rect(10, 19, 1, 5, Y.s);
  n.px(10, 23, Y.d);
  n.line(6, 20, 9, 20, Y.d);
  n.line(6, 22, 8, 22, Y.d);
  n.rect(7, 17, 2, 2, "livre1.b");
  n.px(7, 17, "livre1.hi");
  return cuire(s);
}

/** Le classeur à tiroirs, 20 × 32 : trois tiroirs à porte-étiquette et poignée, deux patins. */
export function classeur(): Sprite {
  const s = sprite(20, 32);
  const g = s.calque();
  const K = R("classeur");
  const M = R("metal");
  const T = R("etiquette");
  g.rect(0, 0, 20, 30, K.s);
  g.rect(0, 0, 20, 1, K.hi);
  g.rect(0, 0, 1, 30, K.b);
  g.rect(19, 1, 1, 29, K.d);
  for (const y of [2, 11, 20]) {
    g.rect(2, y, 16, 8, K.b);
    g.rect(2, y, 16, 1, K.hi);
    g.rect(2, y, 1, 7, K.hi);
    g.rect(17, y + 1, 1, 7, K.s);
    g.rect(2, y + 7, 16, 1, K.d);
    g.rect(7, y + 2, 6, 2, M.s);
    g.rect(8, y + 2, 4, 2, T.b);
    g.px(8, y + 2, T.hi);
    g.px(11, y + 3, T.s);
    g.rect(7, y + 5, 6, 1, M.hi);
    g.rect(8, y + 6, 4, 1, M.s);
  }
  g.rect(1, 30, 3, 2, K.d);
  g.rect(16, 30, 3, 2, K.d);
  return cuire(s);
}

/** La table de réunion, 48 × 24 : plateau veiné, chant épais, pieds massifs, un dossier à chaque bout. */
export function tableDeReunion(): Sprite {
  const s = sprite(48, 24);
  const W = R("bois");
  const Ch = R("chaise");
  const c = s.calque();
  for (const x of [0, 46]) {
    c.rect(x, 6, 2, 8, Ch.b);
    c.rect(x, 6, 2, 1, Ch.hi);
    c.rect(x + 1, 7, 1, 7, Ch.s);
  }
  const g = s.calque();
  g.rect(4, 4, 40, 10, W.b);
  g.rect(4, 4, 40, 1, W.hi);
  g.rect(4, 4, 1, 10, W.hi);
  for (const [x, y, w] of [[8, 6, 12], [24, 6, 9], [12, 8, 7], [27, 9, 13], [6, 11, 10], [21, 11, 6], [35, 7, 6]] as const) g.rect(x, y, w, 1, W.s);
  g.px(30, 9, W.d);
  g.px(14, 6, W.hi);
  g.px(38, 11, W.hi);
  g.rect(4, 14, 40, 2, W.s);
  g.rect(4, 15, 40, 1, W.d);
  for (const x of [8, 36]) {
    g.rect(x, 16, 4, 8, W.s);
    g.rect(x, 16, 1, 8, W.b);
    g.rect(x, 16, 4, 1, W.d);
  }
  return cuire(s);
}

/** La chaise de réunion, 16 × 20 : dossier à barreaux, traverse, assise épaisse, deux pieds visibles. */
export function chaise(): Sprite {
  const s = sprite(16, 20);
  const g = s.calque();
  const W = R("bois");
  g.rect(2, 0, 12, 3, W.b);
  g.rect(2, 0, 12, 1, W.hi);
  g.rect(3, 2, 11, 1, W.s);
  for (const x of [2, 12]) {
    g.rect(x, 1, 2, 9, W.b);
    g.rect(x, 1, 1, 9, W.hi);
    g.px(x + 1, 9, W.s);
  }
  g.rect(13, 1, 1, 9, W.s);
  for (const x of [6, 9]) {
    g.rect(x, 3, 2, 7, W.s);
    g.px(x, 3, W.b);
  }
  g.rect(4, 6, 8, 1, W.b);
  g.rect(4, 7, 8, 1, W.d);
  g.rect(0, 10, 16, 4, W.b);
  g.rect(0, 10, 16, 1, W.hi);
  g.rect(0, 12, 16, 2, W.s);
  g.rect(1, 13, 15, 1, W.d);
  g.clr(0, 10);
  g.clr(15, 10);
  for (const x of [2, 12]) {
    g.rect(x, 14, 2, 6, W.s);
    g.px(x, 14, W.d);
    g.rect(x, 15, 1, 5, W.b);
  }
  return cuire(s);
}

/** Le bureau en bois, 32 × 36 : fauteuil, la figure de la salle assise s'il y en a une, plateau veiné, caisson. */
export function bureauEnBois(figure: { tenue: Tenue; physique: Physique } | null): Sprite {
  const s = sprite(32, 36);
  const Ch = R("chaise");
  const W = R("bois");
  const M = R("metal");
  const ch = s.calque();
  ch.rect(7, 9, 18, 15, Ch.b);
  ch.rect(7, 9, 18, 1, Ch.hi);
  ch.rect(7, 9, 1, 15, Ch.hi);
  ch.rect(24, 10, 1, 14, Ch.s);
  ch.clr(7, 9);
  ch.clr(24, 9);
  for (const [x, y] of [[11, 13], [20, 13], [11, 18], [20, 18]] as const) ch.px(x, y, Ch.d);
  const g = s.calque();
  const a = s.calque();
  if (!figure) {
    ch.rect(6, 19, 20, 5, Ch.s);
    ch.rect(6, 19, 20, 1, Ch.hi);
    ch.rect(6, 20, 20, 2, Ch.b);
  } else {
    const T = R(`haut-${figure.tenue.haut}`);
    const K = R(`peau${figure.physique.peau}`);
    tete(g, 10, 6, figure.physique);
    g.rect(14, 15, 4, 1, K.s);
    g.rect(9, 16, 14, 8, T.b);
    g.rect(8, 17, 16, 7, T.b);
    g.rect(20, 17, 4, 7, T.s);
    g.rect(9, 17, 4, 1, T.hi);
    g.px(9, 18, T.hi);
    if (figure.tenue.cravate) {
      g.rect(13, 16, 6, 1, "col.b");
      g.px(13, 17, "col.b");
      g.px(14, 17, "col.b");
      g.px(17, 17, "col.s");
      g.px(18, 17, "col.s");
      g.rect(15, 16, 2, 1, "cravate.hi");
      g.rect(15, 17, 2, 5, "cravate.b");
      g.px(15, 17, "cravate.hi");
      g.px(16, 22, "cravate.b");
      g.line(13, 18, 14, 21, T.s);
      g.line(18, 18, 17, 21, T.d);
    } else {
      g.rect(13, 16, 2, 2, "col.b");
      g.rect(17, 16, 2, 2, "col.s");
      g.rect(15, 16, 2, 1, K.s);
      for (const y of [19, 21]) g.px(16, y, T.d);
    }
    a.rect(6, 18, 3, 5, T.s);
    a.rect(6, 18, 1, 4, T.d);
    a.rect(23, 18, 3, 5, T.s);
    a.rect(7, 22, 4, 2, K.b);
    a.px(10, 23, K.s);
    a.rect(21, 22, 4, 2, K.b);
    a.px(21, 23, K.s);
  }
  const d = s.calque();
  d.rect(27, 21, 3, 3, M.b);
  d.px(27, 21, M.hi);
  d.rect(29, 21, 1, 3, M.s);
  d.rect(27, 18, 1, 3, "livre1.b");
  d.rect(29, 19, 1, 2, "livre2.b");
  d.px(28, 20, "livre3.b");
  d.rect(2, 24, 28, 1, W.hi);
  d.rect(2, 25, 28, 3, W.b);
  for (const [x, y, w] of [[4, 26, 7], [15, 25, 6], [22, 26, 5], [12, 27, 4]] as const) d.rect(x, y, w, 1, W.s);
  d.rect(2, 28, 28, 2, W.s);
  d.rect(2, 29, 28, 1, W.d);
  d.rect(4, 30, 2, 6, W.s);
  d.rect(4, 30, 1, 6, W.b);
  d.rect(19, 30, 9, 6, W.b);
  d.rect(19, 30, 9, 1, W.d);
  d.rect(27, 31, 1, 5, W.s);
  d.rect(19, 33, 9, 1, W.s);
  d.rect(19, 31, 1, 5, W.hi);
  d.rect(22, 31, 3, 1, M.hi);
  d.rect(22, 34, 3, 1, M.hi);
  return cuire(s);
}
