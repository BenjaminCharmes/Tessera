import type { EtatCase } from "../criteres";
import { TENUES, type Physique } from "../physique";
import { E, type Grille, R, type Sprite, cuire, sprite } from "./grille";
import { tete, torseDetails } from "./poste";

/*
 * Le tableau blanc et les cadres (atelier, `sprites/mur.js`, ticket-727). Seules
 * les cases du tableau portent un état, en jetons `etat-*` (ADR-026, ADR-058).
 */

/** Les mots d'une ligne manuscrite : longueurs fixes par critère, comme une écriture. */
const MOTS = [[9, 5, 13, 7, 11, 6, 8], [6, 11, 4, 9, 14, 7], [12, 4, 8, 10, 6, 13], [7, 9, 5, 12, 8, 11], [10, 6, 9, 4, 13, 7], [5, 12, 7, 8, 10, 9]] as const;
const COCHE = [".....x", "....xx", "x..xx.", "xxxx..", ".xx..."];
const CROIX = ["xx..xx", ".xxxx.", "..xx..", "..xx..", ".xxxx.", "xx..xx"];
/** L'état d'une case → l'état qui la dessine : gris en attente, vert si le critère passe, rouge sinon. */
const ETAT_DE_LA_CASE: Record<EtatCase, string> = { attente: "attente", passe: "fait", echoue: "blocage" };
/** Six lignes par colonne ; au-delà de six critères, une seconde colonne, puis on s'arrête. */
export const CASES_MAX = 12;

/** Le tableau blanc, 88 × 54 : cadre alu, reflet, rebord à feutres ; une case et une ligne par critère. */
export function tableauBlanc(cases: readonly EtatCase[]): Sprite {
  const s = sprite(88, 54);
  const g = s.calque();
  const M = R("metal");
  const T = R("tableau");
  g.rect(0, 0, 88, 54, M.b);
  g.rect(0, 0, 88, 1, M.hi);
  g.rect(0, 0, 1, 54, M.hi);
  g.rect(87, 1, 1, 53, M.s);
  g.rect(1, 53, 87, 1, M.s);
  g.rect(2, 2, 84, 50, T.b);
  g.rect(85, 2, 1, 50, T.s);
  g.rect(2, 51, 84, 1, T.s);
  g.rect(2, 2, 83, 1, T.hi);
  for (let i = 0; i < 6; i++) for (const x of [80, 81, 84]) g.px(x - i, 4 + i, T.hi);
  const largeur = cases.length > 6 ? 30 : 72;
  const m = s.calque();
  cases.slice(0, CASES_MAX).forEach((etat, i) => {
    const x = 4 + Math.floor(i / 6) * 42;
    const y = 4 + (i % 6) * 7;
    const L = E(ETAT_DE_LA_CASE[etat]);
    if (etat === "attente") {
      m.rect(x, y, 6, 6, L.s);
      m.rect(x + 1, y + 1, 4, 4, T.b);
    } else m.stamp(x, y, etat === "passe" ? COCHE : CROIX, { x: L.d });
    let wx = x + 8;
    const fin = x + 8 + largeur;
    for (const n of MOTS[i % 6] ?? []) {
      if (wx >= fin) break;
      const w = Math.min(n, fin - wx);
      m.rect(wx, y + 2, w, 2, L.s);
      if (w > 3) m.px(wx, y + 1, L.s);
      wx += w + 2;
    }
  });
  const r = s.calque();
  r.rect(4, 50, 80, 1, M.hi);
  r.rect(4, 51, 80, 2, M.b);
  r.rect(4, 52, 80, 1, M.s);
  r.rect(58, 48, 8, 2, "encre.b");
  r.rect(58, 48, 2, 2, "encre.hi");
  r.px(66, 49, "encre.b");
  r.rect(70, 47, 9, 2, "bois.b");
  r.rect(70, 47, 9, 1, "bois.hi");
  r.rect(70, 49, 9, 1, "clavier.s");
  return cuire(s);
}

/** Les quatre toiles du cadre, 16 × 20 : paysage, soleil, champ, composition. */
function toile(g: Grille, image: 0 | 1 | 2 | 3, x0: number, y0: number): void {
  const t = (n: number) => R(`toile${n}`);
  const r = (x: number, y: number, w: number, h: number, c: string) => g.rect(x0 + x, y0 + y, w, h, c);
  const p = (x: number, y: number, c: string) => g.px(x0 + x, y0 + y, c);
  if (image === 0) {
    r(0, 0, 16, 12, t(1).b);
    r(0, 0, 16, 3, t(1).s);
    r(0, 9, 16, 3, t(1).hi);
    g.disc(x0 + 12, y0 + 5, 2, "toile3");
    r(0, 12, 16, 8, t(2).b);
    r(0, 11, 7, 1, t(2).b);
    r(2, 10, 3, 1, t(2).b);
    r(11, 11, 5, 1, t(2).s);
    r(9, 13, 7, 7, t(2).s);
    r(1, 11, 3, 1, t(2).hi);
    r(0, 18, 16, 2, t(2).d);
    p(4, 15, t(2).hi);
    p(7, 16, t(2).hi);
  } else if (image === 1) {
    r(0, 0, 16, 20, t(4).b);
    r(0, 0, 16, 3, t(4).s);
    r(0, 12, 16, 4, t(4).hi);
    g.disc(x0 + 7.5, y0 + 7.5, 4, "toile3");
    p(5, 5, t(3).hi);
    r(0, 16, 16, 4, t(2).b);
    r(0, 16, 16, 1, t(2).hi);
    r(10, 17, 6, 3, t(2).s);
  } else if (image === 2) {
    r(0, 0, 16, 20, t(3).b);
    r(0, 0, 16, 2, t(3).hi);
    r(0, 5, 16, 1, t(3).s);
    r(0, 6, 16, 4, t(2).b);
    r(0, 6, 16, 1, t(2).hi);
    r(0, 9, 16, 1, t(2).s);
    for (const [x, y] of [[2, 11], [6, 12], [10, 11], [13, 12], [4, 13]] as const) {
      p(x, y, t(3).s);
      p(x, y - 1, t(3).hi);
    }
    r(0, 14, 16, 6, t(1).b);
    r(0, 14, 16, 1, t(1).hi);
    r(2, 16, 4, 1, t(1).hi);
    r(9, 18, 5, 1, t(1).hi);
    r(0, 19, 16, 1, t(1).s);
  } else {
    r(0, 0, 16, 20, t(2).b);
    r(0, 0, 8, 10, t(4).b);
    r(0, 0, 8, 1, t(4).hi);
    r(7, 1, 1, 9, t(4).s);
    r(8, 10, 8, 10, t(1).b);
    r(8, 10, 8, 1, t(1).hi);
    r(15, 11, 1, 9, t(1).s);
    r(10, 3, 3, 3, t(3).b);
    p(10, 3, t(3).hi);
    r(2, 13, 3, 3, t(2).s);
    r(8, 0, 8, 1, t(2).hi);
    r(0, 19, 8, 1, t(2).s);
  }
}

/** Le cadre, 20 × 24 : baguette en bois en relief, la toile en retrait. Seule l'image varie. */
export function cadre(image: 0 | 1 | 2 | 3): Sprite {
  const s = sprite(20, 24);
  const g = s.calque();
  const W = R("bois");
  g.rect(0, 0, 20, 24, W.b);
  g.rect(0, 0, 20, 1, W.hi);
  g.rect(0, 0, 1, 24, W.hi);
  g.rect(19, 1, 1, 23, W.s);
  g.rect(1, 23, 19, 1, W.s);
  g.rect(1, 1, 18, 1, W.d);
  g.rect(1, 1, 1, 22, W.d);
  g.rect(18, 2, 1, 21, W.hi);
  g.rect(2, 22, 17, 1, W.hi);
  toile(g, image, 2, 2);
  return cuire(s);
}

/** Le cadre de l'employé de la semaine, 32 × 34 : baguette dorée perlée et son étoile, velours uni, buste du codeur. */
export function cadreDore(ph: Physique): Sprite {
  const s = sprite(32, 34);
  const g = s.calque();
  const D = R("dore");
  const V = R("velours");
  const T = R("haut-codeur");
  // Un velours uni : l'auréole claire derrière la tête se lisait, dézoomée, comme une coupe afro.
  g.rect(3, 3, 26, 28, V.s);
  g.rect(3, 3, 26, 1, V.d);
  g.rect(3, 3, 1, 28, V.d);
  tete(g, 10, 12, ph);
  g.rect(14, 21, 4, 1, `peau${ph.peau}.s`);
  g.rect(9, 22, 14, 9, T.b);
  g.rect(8, 23, 16, 8, T.b);
  g.rect(20, 23, 4, 8, T.s);
  g.rect(9, 23, 4, 1, T.hi);
  g.px(9, 24, T.hi);
  torseDetails(g, TENUES.codeur, 9, 22);
  const c = s.calque();
  c.rect(0, 0, 32, 3, D.b);
  c.rect(0, 31, 32, 3, D.b);
  c.rect(0, 0, 3, 34, D.b);
  c.rect(29, 0, 3, 34, D.b);
  c.rect(0, 0, 32, 1, D.hi);
  c.rect(0, 0, 1, 34, D.hi);
  c.rect(31, 1, 1, 33, D.s);
  c.rect(1, 33, 31, 1, D.s);
  for (let x = 3; x < 29; x += 2) {
    c.px(x, 1, D.hi);
    c.px(x, 32, D.s);
  }
  for (let y = 3; y < 31; y += 2) {
    c.px(1, y, D.hi);
    c.px(30, y, D.s);
  }
  c.rect(2, 2, 28, 1, D.d);
  c.rect(2, 2, 1, 30, D.d);
  c.rect(29, 3, 1, 28, D.hi);
  c.rect(3, 31, 27, 1, D.hi);
  for (const [x, y] of [[0, 0], [29, 0], [0, 31], [29, 31]] as const) {
    c.rect(x + 1, y + 1, 2, 2, D.hi);
    c.px(x + 2, y + 2, D.s);
  }
  // Une étoile dorée sur la baguette du haut, hors du portrait : la distinction se lit là.
  c.stamp(13, 0, ["..h..", "hhhhh", ".h.h."], { h: D.hi });
  c.px(15, 1, "etoile.hi");
  c.rect(11, 29, 10, 4, D.s);
  c.rect(12, 29, 8, 3, D.hi);
  for (let x = 13; x < 19; x += 2) c.px(x, 30, D.s);
  return cuire(s);
}
