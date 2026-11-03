import { type Grille, R, type Sprite, cuire, sprite } from "./grille";
import { type ContenuDuSymbole, instanceDuCalque } from "./symboles";

/*
 * Sol, mur, plinthe : des tuiles qui se répètent (atelier, `sprites/ambiance.js`,
 * ticket-727). Une tuile n'est ni contourée ni liserée, sauf le chemin de câbles. Dans le Bureau, elle devient
 * un `<pattern>` du `<defs>` commun : une surface entière coûte un `<rect>`.
 */

/** Le parquet, tuile 64 × 12 : longues lames décalées d'une demi-lame, fil du bois. */
export function solParquet(): Sprite {
  const s = sprite(64, 12);
  const g = s.calque();
  const S = R("sol");
  for (let rang = 0; rang < 2; rang++) {
    const y = rang * 6;
    const decal = rang ? 16 : 0;
    g.rect(0, y, 64, 5, S.b);
    g.rect(0, y, 64, 1, S.hi);
    for (let k = 0; k < 2; k++) {
      const x0 = (k * 32 + decal) % 64;
      if ((k + rang) % 2) for (let x = 1; x < 32; x++) g.rect((x0 + x) % 64, y + 1, 1, 4, S.hi);
      g.rect(x0, y, 1, 5, S.s);
      g.rect((x0 + 5 + rang * 7) % 64, y + 2, 7, 1, S.s);
      g.rect((x0 + 17 + rang * 3) % 64, y + 3, 5, 1, S.s);
    }
    g.rect(0, y + 5, 64, 1, S.d);
  }
  return s;
}

/** Le mur, tuile 32 × 32 : enduit à peine granuleux, un tramage déterministe et clairsemé. */
export function murEnduit(fam = "mur"): Sprite {
  const s = sprite(32, 32);
  const g = s.calque();
  const M = R(fam);
  g.rect(0, 0, 32, 32, M.b);
  for (let i = 0; i < 32 * 32; i++) {
    let h = Math.imul(i ^ 0x9e3779b9, 0x85ebca6b);
    h ^= h >>> 13;
    h = Math.imul(h, 0xc2b2ae35);
    h ^= h >>> 16;
    const v = (h >>> 0) % 100;
    if (v < 3) g.set(i % 32, Math.floor(i / 32), M.hi);
    else if (v < 6) g.set(i % 32, Math.floor(i / 32), M.s);
  }
  return s;
}

/** La plinthe, tuile 16 × 6 : arête éclairée, corps, joint au sol. */
export function plinthe(): Sprite {
  const s = sprite(16, 6);
  const g = s.calque();
  const B = R("plinthe");
  g.rect(0, 0, 16, 6, B.b);
  g.rect(0, 0, 16, 1, B.hi);
  g.rect(0, 5, 16, 1, B.d);
  g.rect(15, 1, 1, 4, B.s);
  return s;
}

/** Une dalle du faux plancher, 24 × 24 : joint, chanfrein éclairé ; perforée, seize trous creusés. */
function dalle(g: Grille, x0: number, perforee: boolean): void {
  const D = R("dalle");
  const r = (x: number, y: number, w: number, h: number, c: string) => g.rect(x0 + x, y, w, h, c);
  r(0, 0, 24, 24, D.s);
  r(0, 0, 24, 1, D.d);
  r(0, 0, 1, 24, D.d);
  r(1, 1, 22, 22, D.b);
  r(1, 1, 22, 1, D.hi);
  r(1, 1, 1, 22, D.hi);
  r(2, 22, 21, 1, D.s);
  r(22, 2, 1, 21, D.s);
  if (perforee) {
    for (const y of [6, 10, 14, 18]) {
      for (const x of [6, 10, 14, 18]) {
        r(x - 1, y - 1, 2, 2, D.d);
        r(x, y, 1, 1, D.s);
      }
    }
  } else {
    ([[5, 7], [15, 4], [9, 15], [18, 17], [12, 10], [4, 19]] as const).forEach(([x, y], i) => r(x, y, 1, 1, i % 2 ? D.s : D.hi));
  }
}

/** Le faux plancher, tuile 96 × 24 : quatre dalles, la deuxième perforée, comme une allée froide. */
export function dalles(): Sprite {
  const s = sprite(96, 24);
  const g = s.calque();
  for (let i = 0; i < 4; i++) dalle(g, i * 24, i === 1);
  return s;
}

const CABLE = [[50, 6], [51, 7], [52, 8], [53, 8], [54, 9], [55, 9], [56, 9], [57, 9], [58, 8], [59, 8], [60, 7], [61, 6]] as const;

/** Le chemin de câbles, tronçon 80 × 16 : caillebotis à fils, câbles vus à travers, une boucle qui pend. */
export function cheminDeCables(): Sprite {
  const s = sprite(80, 16);
  const g = s.calque();
  const M = R("metal");
  const K = R("cadre");
  const Pl = R("salle-plinthe");
  g.rect(0, 6, 80, 2, Pl.b);
  g.rect(0, 7, 80, 1, Pl.d);
  g.rect(0, 0, 80, 1, M.hi);
  g.rect(0, 1, 80, 1, M.b);
  g.rect(0, 2, 80, 4, M.d);
  g.rect(0, 2, 80, 1, K.b);
  g.rect(0, 3, 80, 1, K.s);
  for (let x = 3; x < 80; x += 11) g.px(x, 2, K.hi);
  for (let x = 0; x < 80; x += 4) {
    g.rect(x, 2, 1, 4, M.b);
    g.px(x, 2, M.hi);
    g.px(x + 1, 5, M.s);
  }
  g.rect(0, 4, 80, 1, M.s);
  g.rect(0, 5, 80, 1, M.s);
  for (let x = 0; x < 80; x += 4) g.px(x, 5, M.b);
  const c = s.calque();
  for (const [x, y] of CABLE) {
    c.px(x, y, K.b);
    c.px(x, y + 1, K.d);
  }
  c.px(54, 9, K.hi);
  c.px(55, 9, K.hi);
  return cuire(s);
}

export type Motif = "sol" | "mur" | "salle-mur" | "plinthe" | "dalles" | "chemin";
export type Moment = "jour" | "nuit";

/** Chaque motif : sa tuile et sa taille à l'écran, 1,75 px par pixel comme le poste en grille ×2. */
const MOTIFS: Record<Motif, { tuile: () => Sprite; largeur: number; hauteur: number }> = {
  sol: { tuile: solParquet, largeur: 112, hauteur: 21 },
  mur: { tuile: () => murEnduit(), largeur: 56, hauteur: 56 },
  "salle-mur": { tuile: () => murEnduit("salle-mur"), largeur: 56, hauteur: 56 },
  plinthe: { tuile: plinthe, largeur: 28, hauteur: 10.5 },
  dalles: { tuile: dalles, largeur: 144, hauteur: 36 },
  chemin: { tuile: cheminDeCables, largeur: 120, hauteur: 24 },
};

/** La hauteur de la plinthe à l'écran : les meubles se posent devant elle, sur le sol. */
export const HAUTEUR_DE_LA_PLINTHE = MOTIFS.plinthe.hauteur;

const contenus = new Map<string, ContenuDuSymbole>();

/**
 * Le contenu d'un motif pour un moment. La couleur d'un `<pattern>` se résout là où
 * il est déclaré, pas là où il sert : le motif de nuit se déclare sous
 * `[data-moment="nuit"]` dans le `<defs>`, et la surface choisit le sien.
 */
export function contenuDuMotif(motif: Motif, moment: Moment): ContenuDuSymbole {
  const id = `tuile-${motif}-${moment}`;
  let contenu = contenus.get(id);
  if (!contenu) {
    const { tuile, largeur, hauteur } = MOTIFS[motif];
    const s = tuile();
    const chemins = s.calques.flatMap((c) => instanceDuCalque(c, s.w, s.h)?.symbole.chemins ?? []);
    contenu = { id, w: s.w, h: s.h, chemins, tuile: { largeur, hauteur, moment } };
    contenus.set(id, contenu);
  }
  return contenu;
}
