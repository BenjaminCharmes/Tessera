"use strict";
/* Plantes, machine à café, bibliothèque : du mobilier fixe, grille ×2. */

/** Des touffes de feuillage : disques ombrés, du fond vers l'avant. */
const feuillage = (g, fam, touffes) => touffes.forEach(([cx, cy, r]) => g.disc(cx, cy, r, fam));

/** Un pot qui s'affine : rebord éclairé, terre, flanc droit dans l'ombre. */
function pot(g, Pt, x, y, w, h, terre = P.soil.b) {
  g.rect(x, y, w, 2, Pt.b); g.rect(x, y, w, 1, Pt.hi); if (terre) g.rect(x + 1, y, w - 2, 1, terre);
  g.rect(x, y + 2, w, 1, Pt.d);
  for (let j = 0; j < h; j++) {
    const i = 1 + Math.floor(j / 3);
    g.rect(x + i, y + 3 + j, w - 2 * i, 1, Pt.b); g.px(x + w - i - 1, y + 3 + j, Pt.s); g.px(x + w - i - 2, y + 3 + j, Pt.s); g.px(x + i + 1, y + 3 + j, Pt.hi);
  }
}
function plante(esp) {
  if (esp === "pot") {
    const s = mk(16, 20), g = s.L();
    g.rect(7, 5, 2, 7, P.plant.d);
    feuillage(g, "plante", [[4, 6, 3], [11, 5, 3], [8, 3, 2.6], [3.5, 10, 2.2], [12.5, 9.5, 2.2], [8, 8, 2.4]]);
    pot(g, P.pot, 2, 12, 12, 6);
    return s;
  }
  if (esp === "cactus") {
    const s = mk(16, 20), g = s.L(), K = P.cactus;
    const tronc = (x, y, w, h) => { g.rect(x, y, w, h, K.b); g.rect(x, y, 1, h, K.hi); g.rect(x + w - 1, y, 1, h, K.s); if (w > 3) g.rect(x + 2, y + 1, 1, h - 1, K.s); g.rect(x, y, w, 1, K.hi); g.clr(x, y); g.clr(x + w - 1, y); };
    tronc(6, 2, 4, 12); tronc(2, 5, 3, 5); g.rect(2, 9, 5, 2, K.b); g.rect(2, 10, 5, 1, K.s); tronc(11, 3, 3, 6); g.rect(9, 7, 5, 2, K.b); g.rect(9, 8, 5, 1, K.s);
    [[7, 4], [9, 6], [7, 9], [9, 11], [3, 7], [12, 5], [6, 12]].forEach(([x, y]) => g.px(x, y, P.spine));
    g.rect(7, 0, 2, 2, P.flower.b); g.px(6, 1, P.flower.s); g.px(9, 1, P.flower.s); g.px(7, 0, P.flower.hi);
    pot(g, P.potClair, 3, 13, 10, 5);
    return s;
  }
  const s = mk(16, 32), g = s.L();
  g.rect(7, 16, 2, 7, P.wood.s); g.px(7, 18, P.wood.b); g.px(6, 19, P.wood.s);
  feuillage(g, "plante", [[8, 6, 6], [4, 10, 4], [12, 10, 4], [8, 13, 4.2], [6, 3, 3], [11, 4, 3]]);
  pot(g, P.pot, 2, 22, 12, 8);
  return s;
}
function machineACafe() {
  const s = mk(24, 32), g = s.L(), M = P.machine;
  g.rect(2, 0, 20, 28, M.b); g.rect(2, 0, 20, 2, M.hi); g.rect(2, 0, 2, 28, M.hi); g.rect(19, 2, 3, 26, M.s);
  g.rect(6, 3, 12, 6, M.d); g.rect(7, 4, 10, 4, P.frame.d); g.rect(8, 5, 4, 1, M.s);
  [[7, 10], [11, 10], [15, 10]].forEach(([x, y]) => { g.rect(x, y, 2, 2, M.d); g.px(x, y, M.hi); });
  g.rect(6, 14, 12, 11, M.d); g.rect(10, 14, 4, 3, P.metal.hi); g.rect(11, 17, 2, 1, P.metal.s);
  g.rect(9, 19, 5, 5, P.cup.b); g.rect(9, 19, 5, 1, P.cup.hi); g.rect(10, 19, 3, 1, P.coffee); g.rect(13, 20, 1, 4, P.cup.s); g.rect(14, 20, 1, 2, P.cup.s);
  g.rect(5, 24, 14, 2, M.s); for (let x = 6; x < 18; x += 2) g.px(x, 24, M.d);
  g.rect(0, 28, 24, 4, M.s); g.rect(0, 28, 24, 1, M.b); g.rect(0, 31, 24, 1, M.d);
  return s;
}
function bibliotheque() {
  const s = mk(32, 36), g = s.L(), W = P.wood;
  g.rect(0, 0, 32, 36, W.s); g.rect(0, 0, 32, 2, W.hi); g.rect(0, 0, 2, 36, W.b); g.rect(0, 0, 1, 36, W.hi);
  g.rect(30, 0, 2, 36, W.b); g.rect(31, 1, 1, 35, W.s); g.rect(30, 0, 2, 1, W.hi);
  const rangs = [
    [[3, 3, 8, 1], [6, 2, 7, 2], [8, 3, 8, 3], [11, 2, 6, 1], [14, 3, 8, 2], [17, 3, 7, 3], ["L", 21, 7, 2, 1], [24, 3, 8, 3]],
    [[3, 2, 6, 3], [5, 3, 8, 2], [8, 3, 8, 1], ["L", 12, 8, 2, 3], ["P", 22], [25, 3, 7, 2]],
    [[3, 3, 8, 2], [6, 2, 6, 1], [8, 3, 8, 3], [11, 3, 7, 2], ["L", 15, 6, 2, 1], ["L", 15, 4, 2, 2], [22, 2, 8, 3], [24, 3, 7, 1]],
  ];
  rangs.forEach((livres, i) => {
    const haut = 2 + i * 11, base = haut + 9;
    g.rect(2, haut, 28, 9, W.d);
    for (const b of livres) {
      if (b[0] === "L") { const [, x, w, h, t] = b, B = P.books[t - 1]; g.rect(x, base - h, w, h, B.b); g.rect(x, base - h, w, 1, B.hi); g.rect(x + 1, base - 1, w - 2, 1, B.s); continue; }
      if (b[0] === "P") { const x = b[1]; g.rect(x, base - 3, 3, 3, P.pot.b); g.px(x + 2, base - 2, P.pot.s); feuillage(g, "plante", [[x + 1.5, base - 5, 1.8]]); continue; }
      const [x, w, h, t] = b, B = P.books[t - 1];
      g.rect(x, base - h, w, h, B.b); g.rect(x, base - h, 1, h, B.hi); if (w > 2) g.rect(x + w - 1, base - h, 1, h, B.s); g.rect(x, base - h + 2, w, 1, B.d);
    }
    g.rect(2, base, 28, 1, W.hi); g.rect(2, base + 1, 28, 1, W.b);
  });
  return s;
}

/** Le meuble bas de la machine à café, 32 × 16 : plateau, un tiroir, une porte. */
function meubleBas() {
  const s = mk(32, 16), g = s.L(), W = P.wood, M = P.metal;
  g.rect(0, 0, 32, 3, W.b); g.rect(0, 0, 32, 1, W.hi); g.rect(0, 2, 32, 1, W.s);
  g.rect(1, 3, 30, 13, W.s); g.rect(1, 3, 30, 1, W.d);
  g.rect(3, 5, 26, 3, W.b); g.rect(3, 5, 26, 1, W.hi); g.rect(14, 6, 4, 1, M.hi);
  g.rect(3, 9, 26, 6, W.b); g.rect(3, 9, 1, 6, W.hi); g.rect(28, 9, 1, 6, W.s); g.rect(25, 11, 1, 2, M.hi);
  g.rect(1, 15, 30, 1, W.d);
  return s;
}

enregistrer({ id: "plante", nom: "Plante en pot", fichier: "Plante (pot)", salle: "communs", grille: "8 × 10 → 16 × 20", dw: 40, dh: 50, avant: () => avantPlante("pot"), apres: () => plante("pot"),
  note: "Feuillage en touffes éclairées en haut à gauche, pot en terre cuite qui s'affine, terre visible." });
enregistrer({ id: "cactus", nom: "Cactus", fichier: "Plante (cactus)", salle: "run", grille: "8 × 10 → 16 × 20", dw: 40, dh: 50, avant: () => avantPlante("cactus"), apres: () => plante("cactus"),
  note: "Côtes, épines, une fleur. Le pot clair reste clair." });
enregistrer({ id: "ficus", nom: "Ficus", fichier: "Plante (ficus)", salle: "run", grille: "8 × 16 → 16 × 32", dw: 40, dh: 80, avant: () => avantPlante("ficus"), apres: () => plante("ficus"),
  note: "Une boule de feuillage devient un arbre : tronc en bois, masse feuillue en volume." });
enregistrer({ id: "cafe", nom: "Machine à café", fichier: "MachineACafe", salle: "run", grille: "12 × 16 → 24 × 32", dw: 36, dh: 48, avant: () => avantMachine(), apres: () => machineACafe(),
  note: "Afficheur, trois boutons, buse, grille d'égouttage, tasse pleine. Aucun voyant : rien ne dit qu'on s'en sert." });
enregistrer({ id: "meuble-bas", nom: "Meuble bas de la machine à café", fichier: "nouveau (FondDeLaPiece)", salle: "run", grille: "— → 32 × 16", dw: 48, dh: 24, avant: null, apres: () => meubleBas(),
  note: "La machine à café se pose dessus : sa tasse arrive à hauteur de main d'un agent debout, au lieu d'être au ras du sol." });
enregistrer({ id: "biblio", nom: "Bibliothèque", fichier: "Bibliotheque", salle: "run", grille: "16 × 18 → 32 × 36", dw: 48, dh: 54, avant: () => avantBiblio(), apres: () => bibliotheque(),
  note: "Reliures avec dos et bandeau, livres couchés en pile, une petite plante sur une étagère." });
