import { type Sprite, sprite } from "./grille";
import { type ContenuDuSymbole, instanceDuCalque } from "./symboles";

/*
 * Sol, mur, plinthe : des tuiles qui se répètent (atelier, `sprites/ambiance.js`,
 * ticket-727). Une tuile n'est ni contourée ni liserée. Dans le Bureau, elle devient
 * un `<pattern>` du `<defs>` commun : une surface entière coûte un `<rect>`.
 */

const R = (fam: string) => ({ hi: `${fam}.hi`, b: `${fam}.b`, s: `${fam}.s`, d: `${fam}.d` });

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

export type Motif = "sol" | "mur" | "salle-mur" | "plinthe";
export type Moment = "jour" | "nuit";

/** Chaque motif : sa tuile et sa taille à l'écran, 1,75 px par pixel comme le poste en grille ×2. */
const MOTIFS: Record<Motif, { tuile: () => Sprite; largeur: number; hauteur: number }> = {
  sol: { tuile: solParquet, largeur: 112, hauteur: 21 },
  mur: { tuile: () => murEnduit(), largeur: 56, hauteur: 56 },
  "salle-mur": { tuile: () => murEnduit("salle-mur"), largeur: 56, hauteur: 56 },
  plinthe: { tuile: plinthe, largeur: 28, hauteur: 10.5 },
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
    const calque = s.calques[0];
    const chemins = calque ? (instanceDuCalque(calque, s.w, s.h)?.symbole.chemins ?? []) : [];
    contenu = { id, w: s.w, h: s.h, chemins, tuile: { largeur, hauteur, moment } };
    contenus.set(id, contenu);
  }
  return contenu;
}
