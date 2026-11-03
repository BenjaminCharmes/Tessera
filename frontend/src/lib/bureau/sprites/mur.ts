import { R, type Sprite, cuire, delai, sprite } from "./grille";

/*
 * Le mur de la pièce de run (atelier, `sprites/mur.js`, ticket-727) : fenêtre,
 * plafonnier, horloge, porte, interrupteur. Grille ×2. Le ciel et l'heure sont des
 * données, pas des états (ADR-058).
 */

/** Le ciel derrière la vitre, pixel par pixel : plus sombre en haut, plus clair à l'horizon. */
function ciel(jour: boolean, x: number, y: number): string {
  const trame = (x + y) % 2 === 0;
  if (jour) {
    if (y <= 3 || (y === 4 && trame)) return "ciel.s";
    if (y >= 16 || (y === 15 && trame)) return "ciel.hi";
    return "ciel.b";
  }
  if (y <= 5 || (y === 6 && trame)) return "ciel-nuit.s";
  if (y >= 17 || (y === 16 && trame)) return "ciel-nuit.hi";
  return "ciel-nuit.b";
}

const NUAGE = ["..hhh...", ".hhbbbh.", "hbbbbbbb", ".sssss.."];
const LUNE = ["..bbb", ".hb..", "hb...", "hb...", "hb...", ".hb..", "..bbb"];

export interface OptionsFenetre {
  jour: boolean;
  /** Le jour, le soleil ; la nuit, la même fenêtre porte la lune. */
  soleil: boolean;
  nuages: 0 | 1 | 2;
}

/** La fenêtre, 40 × 24 : ciel en dégradé, soleil ou lune, nuages, étoiles qui scintillent, reflets. */
export function fenetre({ jour, soleil, nuages }: OptionsFenetre): Sprite {
  const s = sprite(40, 24);
  const g = s.calque();
  const F = R("fenetre");
  for (let y = 2; y <= 20; y++) for (let x = 2; x <= 37; x++) g.px(x, y, ciel(jour, x, y));
  const v = s.calque();
  if (jour) {
    if (soleil) {
      v.disc(29, 7, 3, "soleil", { ombre: false });
      v.rect(27, 6, 2, 1, "soleil.hi");
      v.px(28, 5, "soleil.hi");
      v.rect(30, 9, 2, 1, "soleil.s");
      v.px(31, 8, "soleil.s");
    }
    const table = { h: "nuage.hi", b: "nuage.b", s: "nuage.s" };
    if (nuages >= 1) v.stamp(4, 6, NUAGE, table);
    if (nuages >= 2) v.stamp(26, 14, NUAGE, table);
  } else {
    if (soleil) v.stamp(27, 4, LUNE, { h: "etoile.hi", b: "etoile.b" });
    for (const [x, y] of [[12, 14], [32, 16], [16, 5]] as const) v.px(x, y, "etoile.b");
    // Deux étoiles en croix qui scintillent : le décor du ciel, aucun état.
    ([[8, 6], [24, 10]] as const).forEach(([x, y], i) => {
      const e = s.calque("anim-scintille", delai(-i * 1.3));
      e.px(x, y, "etoile.hi");
      for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]] as const) e.px(x + dx, y + dy, "etoile.s");
    });
  }
  const r = s.calque();
  const reflet = jour ? "ciel.hi" : "ciel-nuit.hi";
  r.line(4, 11, 10, 5, reflet);
  r.line(5, 13, 8, 10, reflet);
  r.line(22, 9, 25, 6, reflet);
  const c = s.calque();
  c.rect(0, 0, 40, 2, F.b);
  c.rect(0, 0, 2, 22, F.b);
  c.rect(38, 0, 2, 22, F.b);
  c.rect(0, 20, 40, 1, F.b);
  c.rect(0, 0, 40, 1, F.hi);
  c.rect(0, 0, 1, 21, F.hi);
  c.rect(39, 1, 1, 20, F.s);
  c.rect(2, 1, 36, 1, F.b);
  c.rect(1, 1, 1, 20, F.b);
  c.rect(38, 2, 1, 18, F.d);
  c.rect(19, 2, 2, 18, F.b);
  c.rect(19, 2, 1, 18, F.hi);
  c.rect(20, 2, 1, 18, F.s);
  c.rect(0, 21, 40, 1, F.hi);
  c.rect(0, 22, 40, 1, F.b);
  c.rect(0, 23, 40, 1, F.s);
  c.rect(39, 21, 1, 3, F.d);
  return cuire(s);
}

/** Le plafonnier, 24 × 16 : patère, tige, abat-jour émaillé ; allumé, le diffuseur s'éclaire. */
export function plafonnier(allume: boolean): Sprite {
  const s = sprite(24, 16);
  const g = s.calque();
  const M = R("metal");
  g.rect(8, 0, 8, 2, M.b);
  g.rect(8, 0, 8, 1, M.hi);
  g.rect(15, 1, 1, 1, M.s);
  g.rect(11, 2, 2, 3, M.s);
  g.px(11, 2, M.b);
  g.rect(8, 5, 8, 1, M.b);
  g.rect(6, 6, 12, 1, M.b);
  g.rect(4, 7, 16, 2, M.b);
  g.rect(3, 9, 18, 1, M.s);
  g.rect(9, 5, 3, 1, M.hi);
  g.rect(7, 6, 3, 1, M.hi);
  g.rect(5, 7, 3, 1, M.hi);
  g.rect(14, 6, 4, 1, M.s);
  g.rect(16, 7, 4, 2, M.s);
  g.rect(19, 7, 1, 2, M.d);
  g.rect(17, 9, 4, 1, M.d);
  const d = s.calque();
  if (allume) {
    d.rect(6, 10, 12, 2, "lampe.b");
    d.rect(7, 10, 5, 1, "lampe.hi");
    d.rect(9, 12, 6, 1, "lampe.hi");
  } else {
    d.rect(6, 10, 12, 2, "cadre.b");
    d.rect(7, 10, 3, 1, "cadre.hi");
    d.rect(14, 11, 4, 1, "cadre.s");
  }
  return cuire(s);
}

/** L'horloge, 16 × 16 : cadran rond dans sa lunette, quatre repères, deux aiguilles à l'heure de la vue. */
export function horloge(heure: number, minute: number): Sprite {
  const s = sprite(16, 16);
  s.calque().disc(7.5, 7.5, 7.6, "metal");
  const f = s.calque();
  f.disc(7.5, 7.5, 5.7, "cadran", { ombre: false });
  const dedans = (x: number, y: number) => f.get(x, y) !== null;
  for (let y = 0; y < 16; y++) {
    for (let x = 0; x < 16; x++) {
      if (!dedans(x, y)) continue;
      if (!dedans(x - 1, y - 1)) f.px(x, y, "cadran.s");
      else if (!dedans(x + 1, y + 1)) f.px(x, y, "cadran.hi");
    }
  }
  f.rect(7, 3, 2, 1, "cadran.d");
  f.rect(7, 12, 2, 1, "cadran.d");
  f.rect(3, 7, 1, 2, "cadran.d");
  f.rect(12, 7, 1, 2, "cadran.d");
  const a = s.calque();
  const aiguille = (deg: number, L: number) => {
    const t = (deg * Math.PI) / 180;
    const dx = Math.sin(t);
    const dy = -Math.cos(t);
    a.line(
      Math.floor(7.5 + 1.2 * dx + 0.5 * Math.sign(dx)),
      Math.floor(7.5 + 1.2 * dy + 0.5 * Math.sign(dy)),
      Math.floor(8 + L * dx),
      Math.floor(8 + L * dy),
      "encre.b",
    );
  };
  aiguille((heure % 12) * 30 + minute * 0.5, 3);
  aiguille(minute * 6, 5);
  a.rect(7, 7, 2, 2, "encre.b");
  a.px(7, 7, "metal.hi");
  return cuire(s);
}

/** La porte, 24 × 36 : chambranle, quatre panneaux à plate-bande, poignée en laiton, plaque de propreté. */
export function porte(): Sprite {
  const s = sprite(24, 36);
  const g = s.calque();
  const Pt = R("porte");
  const D = R("dore");
  const M = R("metal");
  g.rect(0, 0, 24, 36, Pt.s);
  g.rect(0, 0, 24, 1, Pt.b);
  g.rect(0, 0, 1, 36, Pt.b);
  g.rect(23, 1, 1, 35, Pt.d);
  g.rect(2, 2, 20, 34, Pt.b);
  g.rect(2, 2, 20, 1, Pt.d);
  g.rect(2, 2, 1, 34, Pt.d);
  g.rect(21, 3, 1, 33, Pt.s);
  g.rect(3, 3, 18, 1, Pt.hi);
  for (const [x, y, w, h] of [[4, 6, 6, 10], [14, 6, 6, 10], [4, 20, 6, 12], [14, 20, 6, 12]] as const) {
    g.rect(x, y, w, h, Pt.s);
    g.rect(x, y, w, 1, Pt.d);
    g.rect(x, y, 1, h, Pt.d);
    g.rect(x + 1, y + h - 1, w - 1, 1, Pt.hi);
    g.rect(x + w - 1, y + 1, 1, h - 1, Pt.hi);
    g.rect(x + 2, y + 2, w - 4, h - 4, Pt.b);
    g.px(x + 2, y + 2, Pt.hi);
  }
  for (const y of [9, 13, 24, 28]) {
    g.px(6, y, Pt.s);
    g.px(16, y + 1, Pt.s);
  }
  g.rect(18, 16, 2, 4, D.s);
  g.rect(17, 17, 3, 2, D.b);
  g.px(17, 17, D.hi);
  g.px(19, 18, D.d);
  g.rect(3, 33, 18, 3, M.b);
  g.rect(3, 33, 18, 1, M.hi);
  g.rect(3, 35, 18, 1, M.s);
  return cuire(s);
}

/** L'interrupteur, 12 × 18 : plaque bombée, deux vis, bascule enfoncée du côté éteint. */
export function interrupteur(allume: boolean): Sprite {
  const s = sprite(12, 18);
  const g = s.calque();
  const I = R("interrupteur");
  const M = R("metal");
  g.rect(0, 0, 12, 18, I.b);
  g.rect(0, 0, 12, 1, I.hi);
  g.rect(0, 0, 1, 18, I.hi);
  g.rect(11, 1, 1, 17, I.s);
  g.rect(1, 17, 11, 1, I.s);
  for (const [x, y] of [[0, 0], [11, 0], [0, 17], [11, 17]] as const) g.clr(x, y);
  g.rect(5, 1, 2, 1, M.s);
  g.px(5, 1, M.b);
  g.rect(5, 16, 2, 1, M.s);
  g.px(5, 16, M.b);
  g.rect(3, 3, 6, 12, I.d);
  const [haut, bas] = allume ? [4, 9] : [9, 4];
  g.rect(4, haut, 4, 5, I.b);
  g.rect(4, haut, 4, 1, I.hi);
  g.rect(4, haut, 1, 5, I.hi);
  g.rect(4, bas, 4, 5, I.s);
  g.rect(7, bas, 1, 5, I.d);
  return cuire(s);
}
