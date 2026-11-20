import type { EtatBoite } from "../boiteAuxLettres";
import type { BoulesDeLaCorbeille } from "../corbeille";
import { E, type Grille, R, type Sprite, cuire, delai, sprite } from "./grille";

/*
 * Les objets de la pièce de run (atelier, `sprites/objets.js`, ticket-727) :
 * imprimante, dossier, corbeille, boîte aux lettres, gyrophare, vapeur, confettis.
 * Seuls le drapeau de la boîte et le gyrophare portent un état (ADR-058), en
 * jetons `etat-*`. La corbeille et la lettre de la boîte rendent une donnée.
 */

/** Le meuble bas et son imprimante, 48 × 28 : bac d'entrée, feuille imprimée, deux portes. */
export function imprimante(): Sprite {
  const s = sprite(48, 28);
  const g = s.calque();
  const I = R("imprimante");
  const Pa = R("papier");
  const W = R("bois");
  const M = R("metal");
  g.rect(6, 0, 10, 2, Pa.b);
  g.rect(6, 0, 10, 1, Pa.hi);
  g.rect(15, 1, 1, 1, Pa.s);
  g.rect(4, 1, 14, 3, I.s);
  g.rect(4, 1, 14, 1, I.b);
  g.rect(5, 2, 12, 1, I.d);
  g.rect(2, 4, 18, 8, I.b);
  g.rect(2, 4, 18, 1, I.hi);
  g.rect(2, 4, 1, 8, I.hi);
  g.rect(18, 5, 2, 7, I.s);
  g.rect(3, 11, 17, 1, I.s);
  // Un afficheur éteint et deux touches : aucun voyant, l'imprimante ne rend aucun état.
  g.rect(14, 6, 4, 1, "cadre.d");
  g.rect(14, 7, 4, 1, I.hi);
  g.px(14, 9, I.d);
  g.px(16, 9, I.d);
  g.rect(4, 7, 9, 1, I.d);
  g.rect(5, 8, 7, 3, Pa.b);
  g.rect(5, 8, 7, 1, Pa.hi);
  g.rect(6, 9, 4, 1, Pa.s);
  g.rect(6, 10, 3, 1, Pa.s);
  g.rect(11, 9, 1, 2, Pa.s);
  g.rect(0, 12, 48, 4, W.b);
  g.rect(0, 12, 48, 1, W.hi);
  g.rect(0, 15, 48, 1, W.s);
  g.rect(2, 16, 44, 12, W.s);
  g.rect(2, 16, 44, 1, W.d);
  for (const x of [4, 25]) {
    g.rect(x, 18, 19, 9, W.b);
    g.rect(x, 18, 19, 1, W.hi);
    g.rect(x, 18, 1, 9, W.hi);
    g.rect(x + 18, 19, 1, 8, W.s);
    g.rect(x + 1, 26, 18, 1, W.s);
  }
  for (const x of [21, 26]) {
    g.rect(x, 21, 1, 3, M.hi);
    g.px(x, 23, M.s);
  }
  g.rect(2, 27, 44, 1, W.d);
  return cuire(s);
}

/** Un dossier de la pile, 20 × 16 : onglet, feuilles qui dépassent, étiquette. */
export function dossier(): Sprite {
  const s = sprite(20, 16);
  const g = s.calque();
  const D = R("dossier");
  const Pa = R("papier");
  g.rect(0, 0, 8, 3, D.s);
  g.rect(0, 0, 7, 1, D.b);
  g.rect(0, 2, 20, 4, D.s);
  g.rect(3, 2, 15, 3, Pa.s);
  g.rect(2, 3, 15, 2, Pa.b);
  g.rect(2, 3, 15, 1, Pa.hi);
  g.rect(0, 5, 20, 11, D.b);
  g.rect(0, 5, 20, 1, D.hi);
  g.rect(0, 5, 1, 10, D.hi);
  g.rect(19, 6, 1, 10, D.s);
  g.rect(0, 15, 20, 1, D.d);
  g.rect(3, 8, 9, 4, Pa.b);
  g.rect(3, 8, 9, 1, Pa.hi);
  g.rect(4, 9, 6, 1, Pa.s);
  g.rect(4, 10, 4, 1, Pa.s);
  g.rect(11, 9, 1, 3, Pa.s);
  return cuire(s);
}

const BOULE = [".hhb..", "hhbsb.", "hbsbbs", "bbbsbs", ".bsbss", "..sss."];
/** Où se pose chaque boule : les deux de devant, puis celle du dessus. */
const PLACES_BOULES = [[2, 4], [10, 4], [6, 2]] as const;

/** La corbeille, 20 × 24 : seau perforé qui s'affine, rebord roulé ; une boule par refus du reviewer. */
export function corbeille(boules: BoulesDeLaCorbeille): Sprite {
  const s = sprite(20, 24);
  const M = R("metal");
  const b = s.calque();
  const table = { h: "papier.hi", b: "papier.b", s: "papier.s" };
  // La boule du dessus d'abord : celles de devant la recouvrent.
  const ordre = PLACES_BOULES.slice(0, boules);
  for (const [x, y] of [...ordre.slice(2), ...ordre.slice(0, 2)]) b.stamp(x, y, BOULE, table);
  const g = s.calque();
  for (let y = 12; y < 24; y++) {
    const i = y >= 18 ? 3 : 2;
    g.rect(i, y, 20 - 2 * i, 1, M.b);
    g.px(i, y, M.hi);
    g.rect(19 - i - 1, y, 2, 1, M.s);
  }
  g.rect(2, 12, 16, 1, M.d);
  for (const y of [14, 17, 20]) for (let x = 5; x < 16; x += 3) g.px(x + (y === 17 ? 1 : 0), y, M.d);
  g.rect(3, 23, 14, 1, M.d);
  g.rect(0, 10, 20, 2, M.b);
  g.rect(0, 10, 20, 1, M.hi);
  g.rect(18, 11, 2, 1, M.s);
  return cuire(s);
}

/** Le drapeau de la boîte, par état de la PR : un état, jamais une famille thémée (ADR-026). */
const DRAPEAU: Record<Exclude<EtatBoite, "aucune">, string> = { ouverte: "question", ci: "actif", mergee: "fait", refusee: "blocage" };

/** La boîte aux lettres, 24 × 24 : dos arrondi, porte et fente ; drapeau et lettre s'il y a une PR. */
export function boite(etat: EtatBoite): Sprite {
  const s = sprite(24, 24);
  const g = s.calque();
  const B = R("boite");
  const M = R("metal");
  const Pa = R("papier");
  g.stamp(7, 20, ["b.b", "bbb"], { b: "plante.s" });
  g.stamp(15, 20, [".b.", "bbs"], { b: "plante.s", s: "plante.d" });
  g.rect(10, 16, 4, 8, M.b);
  g.rect(10, 16, 1, 8, M.hi);
  g.rect(13, 16, 1, 8, M.s);
  g.rect(10, 16, 4, 1, M.d);
  g.rect(4, 6, 14, 1, B.b);
  g.rect(3, 7, 16, 1, B.b);
  g.rect(2, 8, 18, 8, B.b);
  g.rect(4, 6, 12, 1, B.hi);
  g.rect(3, 7, 2, 1, B.hi);
  g.rect(2, 8, 1, 7, B.hi);
  g.rect(18, 8, 2, 8, B.s);
  g.rect(3, 15, 17, 1, B.d);
  g.rect(4, 8, 1, 7, B.s);
  g.rect(3, 11, 1, 2, M.hi);
  if (etat !== "aucune") {
    g.rect(8, 8, 6, 2, Pa.b);
    g.rect(8, 8, 6, 1, Pa.hi);
    g.px(13, 9, Pa.s);
  }
  g.rect(7, 10, 9, 1, B.d);
  g.rect(7, 11, 9, 1, B.hi);
  g.rect(20, 10, 2, 2, M.s);
  g.px(20, 10, M.hi);
  if (etat !== "aucune") {
    const L = E(DRAPEAU[etat]);
    const d = s.calque();
    d.rect(20, 2, 2, 9, L.s);
    d.rect(20, 2, 1, 9, L.b);
    d.rect(15, 2, 5, 4, L.b);
    d.rect(15, 2, 5, 1, L.hi);
    d.rect(15, 5, 5, 1, L.s);
  }
  return cuire(s);
}

/**
 * Le gyrophare, 20 × 16 : dôme strié et éclats en tons d'état (blocage), qui clignotent ;
 * socle fixe. Suspendu, il pend tête en bas sous le plafonnier, son socle vissé au-dessus.
 */
export function gyrophare(suspendu = false): Sprite {
  const s = sprite(20, 16);
  const L = E("blocage");
  const M = R("metal");
  const d = s.calque("anim-gyro");
  d.rect(7, 0, 6, 1, L.s);
  d.rect(6, 1, 8, 1, L.b);
  d.rect(5, 2, 10, 8, L.b);
  d.rect(5, 2, 1, 8, L.hi);
  d.rect(13, 2, 2, 8, L.s);
  for (const x of [7, 11]) d.rect(x, 3, 1, 7, L.s);
  d.rect(8, 3, 3, 4, L.hi);
  d.rect(1, 5, 2, 1, L.hi);
  d.px(2, 2, L.b);
  d.px(3, 3, L.b);
  d.rect(17, 5, 2, 1, L.hi);
  d.px(17, 2, L.b);
  d.px(16, 3, L.b);
  const g = s.calque();
  g.rect(4, 10, 12, 1, M.d);
  g.rect(3, 11, 14, 5, M.b);
  g.rect(3, 11, 14, 1, M.hi);
  g.rect(3, 11, 1, 5, M.hi);
  g.rect(15, 12, 2, 4, M.s);
  g.rect(4, 15, 13, 1, M.d);
  g.px(5, 13, M.d);
  g.px(14, 13, M.d);
  if (suspendu) for (const { g: c } of s.calques) retourner(c);
  return cuire(s);
}

/** Retourne une grille de haut en bas, avant la cuisson : le liseré reste en haut à gauche. */
function retourner(g: Grille): void {
  const lignes = Array.from({ length: g.h }, (_, y) => g.p.slice(y * g.w, (y + 1) * g.w));
  lignes.reverse().forEach((ligne, y) => ligne.forEach((c, x) => (g.p[y * g.w + x] = c)));
}

const VOLUTE = ["..h.", ".h..", ".b..", ".bb.", "..bb", "..bb", ".bb.", ".bs.", "bs.."];
const VOLUTE_HAUTE = [".h..", "h...", "b...", "bb..", ".bb.", "..bb", "..bb", ".bb.", ".bs.", "bs.."];
const miroir = (lignes: readonly string[]) => lignes.map((l) => [...l].reverse().join(""));

/** La vapeur du café, 24 × 16 : trois volutes en S qui montent chacune à son rythme. */
export function vapeur(): Sprite {
  const s = sprite(24, 16);
  const table = { h: "vapeur.hi", b: "vapeur.b", s: "vapeur.s" };
  s.calque("anim-vapeur", delai(-0.4)).stamp(5, 6, VOLUTE, table);
  s.calque("anim-vapeur").stamp(9, 1, VOLUTE_HAUTE, table);
  s.calque("anim-vapeur", delai(-0.9)).stamp(15, 4, miroir(VOLUTE), table);
  return cuire(s);
}

/** Les cinq formes de confetti, 4 × 6 : à plat, incliné, en lanière, de chant, penché. */
const FORMES_CONFETTI = [
  ["hhbb", "hbbs", "hbbs", "hbbs", "hbbs", "bbss"],
  ["hb..", "hbb.", "bbbs", ".bbs", "..bs", "...s"],
  ["...h", "..hb", "..bs", ".bs.", ".bs.", "bs.."],
  [".hb.", ".hb.", ".bs.", ".bs.", ".bs.", ".ss."],
  ["..hb", ".hbb", "hbbs", "bbs.", "bs..", "s..."],
] as const;

/** Un confetti, 4 × 6, dans son ton (1 à 5) : un sprite par forme, posé et animé par la pièce. */
export function confetti(i: number): Sprite {
  const s = sprite(4, 6);
  const n = (i % 5) + 1;
  const g: Grille = s.calque();
  g.stamp(0, 0, FORMES_CONFETTI[i % 5] ?? [], { h: `confetti${n}.hi`, b: `confetti${n}.b`, s: `confetti${n}.s` });
  return cuire(s);
}

/**
 * Le marqueur d'anomalie, 9 × 8 (ADR-078, ticket-832) : un triangle d'avertissement en ton
 * `etat-anomalie` (ambre), son point d'exclamation dans le creux. Posé au-dessus du poste
 * de l'agent dont le run porte une anomalie : un seul par run, jamais par anomalie. Un
 * voyant garde sa teinte (ADR-026), donc ni contour ni liseré de nuit.
 */
export function marqueurAnomalie(): Sprite {
  const s = sprite(9, 8);
  const g = s.calque();
  const A = E("anomalie");
  // Le triangle, du sommet à la base : 1, 3, 3, 5, 5, 7, 7, 9 pixels de large.
  const demi = [0, 1, 1, 2, 2, 3, 3, 4];
  demi.forEach((d, y) => {
    g.rect(4 - d, y, 2 * d + 1, 1, A.b);
    g.px(4 - d, y, A.hi);
    g.px(4 + d, y, A.s);
  });
  g.rect(0, 7, 9, 1, A.s);
  g.rect(4, 2, 1, 3, A.d);
  g.px(4, 6, A.d);
  return s;
}
