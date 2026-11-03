import type { Physique, Tenue } from "../physique";
import { type Grille, type Sprite, cuire, sprite } from "./grille";

/*
 * La tête et le poste, portés de l'atelier (`sprites/personnages.js`) pour le
 * pilote du ticket-727. Grille ×2 de l'ancien poste : 40 × 36 au lieu de 20 × 18,
 * pour la même taille à l'écran.
 */

/** L'expression du visage : elle suit la santé de l'agent. */
export type Expression = "neutre" | "actif" | "attente" | "question" | "blocage" | "fait";

/** Les cinq tons d'une famille. */
const R = (fam: string) => ({ hi: `${fam}.hi`, b: `${fam}.b`, s: `${fam}.s`, d: `${fam}.d`, bl: `${fam}.bl` });
const ENCRE = "encre.b";

/** La tête : visage 12 × 9 en (x, y), cheveux au-dessus. */
export function tete(g: Grille, x: number, y: number, ph: Physique, expr: Expression = "neutre"): void {
  const H = R(`cheveux${ph.cheveux}`);
  const K = R(`peau${ph.peau}`);
  const br = H.s;
  g.rect(x - 1, y + 4, 1, 2, K.s);
  g.rect(x + 12, y + 4, 1, 2, K.s);
  g.rect(x, y, 12, 9, K.b);
  g.rect(x + 11, y + 1, 1, 7, K.s);
  g.rect(x + 1, y + 8, 10, 1, K.s);
  g.clr(x, y + 8);
  g.clr(x + 11, y + 8);
  g.rect(x + 1, y + 1, 1, 3, K.hi);
  if (ph.coiffure === "long") {
    g.rect(x - 2, y - 1, 2, 13, H.b);
    g.rect(x + 12, y - 1, 2, 13, H.s);
    g.rect(x - 2, y + 11, 2, 1, H.s);
    g.rect(x + 12, y + 11, 2, 1, H.d);
  }
  if (ph.coiffure === "carre") {
    g.rect(x - 2, y - 1, 2, 8, H.b);
    g.rect(x + 12, y - 1, 2, 8, H.s);
    g.rect(x - 2, y + 6, 2, 1, H.s);
  }
  if (ph.coiffure === "chauve") {
    g.rect(x + 1, y - 2, 10, 2, K.b);
    g.rect(x, y - 1, 12, 1, K.b);
    g.rect(x + 3, y - 2, 3, 1, K.hi);
    g.rect(x + 9, y - 1, 2, 1, K.s);
    g.rect(x - 1, y + 1, 2, 4, H.b);
    g.rect(x + 11, y + 1, 2, 4, H.s);
  } else {
    g.rect(x + 1, y - 3, 10, 1, H.b);
    g.rect(x, y - 2, 12, 2, H.b);
    g.rect(x, y, 12, 1, H.b);
    for (const dx of [2, 3, 7]) g.px(x + dx, y + 1, H.b);
    g.px(x + 10, y + 1, H.s);
    g.rect(x + 9, y - 2, 3, 3, H.s);
    g.rect(x + 3, y - 2, 3, 1, H.hi);
    g.px(x + 2, y - 1, H.hi);
    if (ph.coiffure === "court") {
      g.rect(x, y, 1, 3, H.b);
      g.rect(x + 11, y, 1, 3, H.s);
    }
  }
  const yeux = (dx = 0) => {
    g.rect(x + 3 + dx, y + 4, 1, 2, ENCRE);
    g.rect(x + 8 + dx, y + 4, 1, 2, ENCRE);
  };
  const joues = () => {
    g.px(x + 2, y + 6, K.bl);
    g.px(x + 9, y + 6, K.bl);
  };
  switch (expr) {
    case "actif":
      g.rect(x + 2, y + 3, 2, 1, br);
      g.rect(x + 8, y + 3, 2, 1, br);
      yeux(1);
      g.rect(x + 5, y + 7, 2, 1, K.d);
      break;
    case "attente":
      g.rect(x + 2, y + 5, 2, 1, ENCRE);
      g.rect(x + 8, y + 5, 2, 1, ENCRE);
      g.px(x + 6, y + 7, K.d);
      joues();
      break;
    case "question":
      g.rect(x + 2, y + 3, 2, 1, br);
      g.rect(x + 8, y + 2, 2, 1, br);
      yeux();
      g.px(x + 6, y + 7, ENCRE);
      joues();
      break;
    case "blocage":
      g.px(x + 2, y + 2, br);
      g.px(x + 3, y + 3, br);
      g.px(x + 9, y + 2, br);
      g.px(x + 8, y + 3, br);
      yeux();
      g.rect(x + 4, y + 7, 4, 1, K.d);
      g.px(x + 13, y + 1, "sueur.hi");
      g.rect(x + 12, y + 2, 2, 2, "sueur.b");
      break;
    case "fait":
      for (const [a, b] of [[2, 5], [3, 4], [4, 5], [7, 5], [8, 4], [9, 5]] as const) g.px(x + a, y + b, ENCRE);
      g.px(x + 4, y + 6, K.d);
      g.rect(x + 5, y + 7, 2, 1, K.d);
      g.px(x + 7, y + 6, K.d);
      joues();
      break;
    default:
      g.rect(x + 2, y + 3, 2, 1, br);
      g.rect(x + 8, y + 3, 2, 1, br);
      yeux();
      g.rect(x + 5, y + 7, 2, 1, K.d);
      joues();
  }
}

/** Ce qui distingue une tenue : capuche à cordons, ou col et cravate. */
export function torseDetails(g: Grille, tenue: Tenue, x: number, y: number): void {
  const T = R(`haut-${tenue.haut}`);
  if (tenue.capuche) {
    g.rect(x + 3, y, 8, 2, T.s);
    g.rect(x + 4, y, 6, 1, T.d);
    g.rect(x + 5, y + 2, 1, 3, T.hi);
    g.rect(x + 8, y + 2, 1, 2, T.hi);
    g.rect(x + 3, y + 5, 8, 2, T.s);
  }
  if (tenue.cravate) {
    g.rect(x + 4, y, 2, 1, "col.b");
    g.rect(x + 8, y, 2, 1, "col.s");
    g.rect(x + 6, y, 2, 2, "cravate.hi");
    g.rect(x + 6, y + 2, 2, 5, "cravate.b");
    g.px(x + 7, y + 7, "cravate.b");
  }
}

/** L'état que montre l'écran quand il n'a pas de scène : la teinte de l'état (ADR-026). */
export type EtatEcran = "actif" | "attente" | "question" | "blocage" | "fait";

export interface OptionsPoste {
  physique: Physique;
  tenue: Tenue;
  /** Sans personne : la chaise vide, l'écran en veille. */
  vide: boolean;
  expression: Expression;
  /** Les mains tapent : l'agent travaille. */
  tape: boolean;
  etatEcran: EtatEcran;
  /** L'écran porte une scène (dessinée à part, par `EcranScene`) : on ne dessine que son fond. */
  scene: boolean;
}

/** Le poste, grille 40 × 36. Calques : chaise, agent, bureau, mains, écran, lueur. */
export function poste(o: OptionsPoste): Sprite {
  const s = sprite(40, 36);
  const T = R(`haut-${o.tenue.haut}`);
  const K = R(`peau${o.physique.peau}`);
  const C = R("chaise");
  const ch = s.calque();
  ch.rect(6, 13, 18, 11, C.s);
  ch.rect(7, 12, 16, 1, C.b);
  ch.rect(7, 13, 16, 1, C.hi);
  ch.rect(14, 28, 2, 5, C.s);
  ch.rect(14, 28, 1, 5, C.b);
  ch.rect(9, 33, 12, 1, C.d);
  ch.rect(10, 33, 10, 1, C.s);
  for (const x of [9, 14, 20]) ch.px(x, 34, C.d);
  const g = s.calque();
  if (!o.vide) {
    tete(g, 9, 6, o.physique, o.expression);
    g.rect(13, 15, 4, 1, K.s);
    g.rect(8, 16, 14, 8, T.b);
    g.rect(7, 17, 16, 7, T.b);
    g.rect(19, 17, 4, 7, T.s);
    g.rect(8, 17, 4, 1, T.hi);
    g.px(8, 18, T.hi);
    torseDetails(g, o.tenue, 8, 16);
    for (const x of [10, 17]) {
      g.rect(x, 28, 3, 6, "pantalon.b");
      g.rect(x + 2, 28, 1, 6, "pantalon.s");
      g.rect(x - 1, 34, 4, 2, "chaussure.b");
      g.rect(x - 1, 34, 4, 1, "chaussure.hi");
    }
  } else {
    ch.rect(6, 20, 18, 4, C.b);
    ch.rect(6, 20, 18, 1, C.hi);
  }
  const D = R("bureau");
  const d = s.calque();
  d.rect(10, 23, 10, 1, "clavier.hi");
  d.rect(2, 24, 36, 1, D.hi);
  d.rect(2, 25, 36, 2, D.b);
  d.rect(2, 27, 36, 1, D.s);
  d.rect(4, 28, 2, 8, D.s);
  d.rect(34, 28, 2, 8, D.s);
  d.rect(4, 28, 2, 1, D.d);
  d.rect(34, 28, 2, 1, D.d);
  const a = s.calque(o.tape && !o.vide ? "anim-tape" : "");
  if (!o.vide) {
    a.rect(5, 18, 3, 5, T.s);
    a.rect(22, 18, 3, 5, T.s);
    a.rect(5, 18, 1, 4, T.d);
    a.rect(5, 22, 3, 2, K.b);
    a.rect(22, 22, 3, 2, K.b);
    a.px(7, 23, K.s);
    a.px(24, 23, K.s);
  }
  const F = R("cadre");
  const e = s.calque();
  e.rect(24, 10, 16, 12, F.b);
  e.rect(24, 10, 16, 1, F.hi);
  e.rect(24, 11, 1, 10, F.hi);
  e.rect(39, 11, 1, 11, F.s);
  e.rect(25, 21, 15, 1, F.s);
  e.rect(31, 22, 2, 1, F.s);
  e.rect(28, 23, 8, 1, F.b);
  const etat = o.vide ? "attente" : o.etatEcran;
  const L = R(`etat-${etat}`);
  const l = s.calque(etat === "actif" && !o.scene ? "anim-lueur" : "");
  l.rect(26, 12, 12, 8, o.vide ? "cadre.d" : L.d);
  if (o.vide || o.scene) return eclairer(cuire(s), etat);
  // En attente : trois points de veille au centre de l'écran, l'agent reste net.
  if (etat === "attente") for (const x of [28, 31, 34]) l.rect(x, 15, 2, 2, L.hi);
  else if (etat === "fait") {
    for (const [x, y] of [[29, 16], [30, 17], [31, 18], [32, 17], [33, 16], [34, 15], [35, 14]] as const) l.px(x, y, L.hi);
  } else {
    l.rect(27, 13, 5, 1, L.hi);
    l.rect(33, 13, 3, 1, L.b);
    l.rect(28, 15, 7, 1, L.b);
    l.rect(28, 17, 4, 1, L.b);
    l.rect(33, 17, 2, 1, L.hi);
    l.rect(27, 19, 3, 1, L.s);
    l.px(37, 12, L.hi);
  }
  return eclairer(cuire(s), etat);
}

/**
 * La nuit, l'écran éclaire l'agent et ses mains (calques 1 et 3), en trois paliers.
 * Le jeton porte la marque « ^etat^palier » ; le jour, sa force CSS est nulle.
 */
function eclairer(s: Sprite, etat: EtatEcran, cx = 32, cy = 16): Sprite {
  for (const k of [1, 3]) {
    const calque = s.calques[k];
    if (!calque) continue;
    const { g } = calque;
    g.p.forEach((c, i) => {
      if (!c) return;
      const x = i % s.w;
      const y = Math.floor(i / s.w);
      const d = Math.hypot(x - cx, (y - cy) * 1.3);
      const n = d < 12 ? 3 : d < 16 ? 2 : d < 20 ? 1 : 0;
      if (n) g.p[i] = `${c}^${etat}^${n}`;
    });
  }
  return s;
}
