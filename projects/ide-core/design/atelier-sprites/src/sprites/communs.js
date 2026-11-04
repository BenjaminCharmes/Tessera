"use strict";
/* Salles communes : pause, réunion, RH, bureau du directeur. Grille ×2. Du mobilier fixe (ADR-058) :
   seul l'écran de la console porte un état, celui que le produit déclare pour son agent. */

Object.assign(FAMILLES, {
  canape: { tessera: "#57534e", chaud: "#8a4f36", neon: "#33285a" },
  coussin: { tessera: "#a16207", chaud: "#c9853a", neon: "#a8488f" },
  frigo: { tessera: "#e7e5e4", chaud: "#eee4cc", neon: "#4c5590" },
  postit: { tessera: "#fde047", chaud: "#f5cf5a", neon: "#ffd23d" },
  classeur: { tessera: "#71717a", chaud: "#6e7a68", neon: "#30345a" },
  etiquette: { tessera: "#f4f4f5", chaud: "#efe4c8", neon: "#8a8fc0" },
});
Object.assign(C, {
  canape: "#57534e", canapeO: "#44403c", frigo: "#e7e5e4", frigoO: "#a8a29e", classeur: "#71717a", classeurO: "#52525b",
  consEcran: "#0f172a", consAllume: "#172554", consTexte: "#93c5fd", consTouche: "#a1a1aa",
});
/** Le directeur et la recruteuse : tenue et physique tirés comme dans `lib/bureau/sallesCommunes`. */
const COM_FIGURES = {
  directeur: { haut: "securite", cravate: true, ph: { peau: 2, cheveux: 2, coiffure: "carre" } },
  rh: { haut: "validateur", cravate: false, ph: { peau: 5, cheveux: 4, coiffure: "court" } },
};

/* ---------- Copies fidèles ---------- */
function avantCanape() {
  const s = mk(24, 10), g = s.L();
  g.rect(2, 0, 20, 5, C.canape); g.rect(0, 3, 3, 6, C.canapeO); g.rect(21, 3, 3, 6, C.canapeO);
  g.rect(3, 5, 18, 3, C.canape); g.rect(3, 8, 18, 1, C.canapeO); g.rect(1, 9, 1, 1, C.tableO); g.rect(22, 9, 1, 1, C.tableO);
  return s;
}
function avantFrigo() {
  const s = mk(10, 18), g = s.L();
  g.rect(0, 0, 10, 18, C.frigoO); g.rect(1, 1, 8, 5, C.frigo); g.rect(1, 7, 8, 10, C.frigo);
  g.rect(7, 3, 1, 2, C.frigoO); g.rect(7, 8, 1, 3, C.frigoO);
  return s;
}
function avantClasseur() {
  const s = mk(10, 16), g = s.L();
  g.rect(0, 0, 10, 16, C.classeurO);
  for (const y of [1, 6, 11]) { g.rect(1, y, 8, 4, C.classeur); g.rect(4, y + 1, 2, 1, C.classeurO); }
  return s;
}
function avantTableReunion() {
  const s = mk(24, 12), g = s.L();
  g.rect(2, 2, 20, 5, C.table); g.rect(2, 7, 20, 1, C.tableO); g.rect(4, 8, 2, 4, C.tableO); g.rect(18, 8, 2, 4, C.tableO);
  g.rect(0, 3, 1, 3, C.machineO); g.rect(23, 3, 1, 3, C.machineO);
  return s;
}
function avantChaise() {
  const s = mk(8, 10), g = s.L();
  g.rect(1, 0, 6, 5, C.tableO); g.rect(0, 5, 8, 2, C.table); g.rect(1, 7, 1, 3, C.tableO); g.rect(6, 7, 1, 3, C.tableO);
  return s;
}
function avantBureauEnBois(qui = "directeur", vide = false) {
  const s = mk(16, 18), g = s.L(), F = COM_FIGURES[qui];
  if (!vide) {
    avantTete(g, F.ph, 5, 3);
    g.rect(4, 7, 8, 5, C.haut[F.haut]);
    if (F.cravate) { g.rect(7, 7, 2, 1, C.col); g.rect(7, 8, 2, 3, C.cravate); }
    g.rect(3, 9, 2, 3, C.ombre[F.haut]); g.rect(11, 9, 2, 3, C.ombre[F.haut]);
  }
  g.rect(1, 12, 14, 2, C.table); g.rect(1, 14, 14, 1, C.tableO); g.rect(2, 15, 1, 3, C.tableO); g.rect(13, 15, 1, 3, C.tableO);
  return s;
}
/** La console a des lignes de texte en demi-unités : la copie se fait sur une grille déjà doublée, coordonnées × 2. */
function avantConsole(allume = true) {
  const s = mk(40, 36), g = s.L(), r = (x, y, w, h, c) => g.rect(x * 2, y * 2, w * 2, h * 2, c);
  r(13, 3, 6, 6, C.metalO); r(14, 4, 4, 4, allume ? C.consAllume : C.consEcran);
  if (allume) [[9, 6], [11, 4], [13, 6], [15, 3]].forEach(([y, w]) => g.rect(29, y, w, 1, C.consTexte));
  r(15, 9, 2, 3, C.metalO); r(14, 11, 4, 1, C.metal); r(1, 12, 18, 2, C.metalC); r(1, 14, 18, 1, C.metalO);
  for (const x of [4, 6, 8, 10, 12, 14]) r(x, 12, 1, 1, C.consTouche);
  r(2, 15, 1, 3, C.metal); r(17, 15, 1, 3, C.metal);
  return s;
}

/* ---------- Grille ×2 ---------- */
/** Un coussin rembourré : dessus éclairé, flanc droit et dessous dans l'ombre, coins arrondis, bouton au centre. */
function comCoussin(g, K, x, y, w, h, bouton = true) {
  g.rect(x, y, w, h, K.b); g.rect(x, y, w, 1, K.hi); g.rect(x, y, 1, h - 1, K.hi);
  g.rect(x + w - 1, y + 1, 1, h - 1, K.s); g.rect(x + 1, y + h - 1, w - 1, 1, K.s);
  g.clr(x, y); g.clr(x + w - 1, y);
  if (bouton) g.px(x + (w >> 1), y + (h >> 1), K.d);
}
function comCanape() {
  const s = mk(48, 20), g = s.L(), K = R("canape"), W = P.wood;
  g.rect(4, 0, 40, 11, K.d);
  for (const x of [5, 18, 31]) comCoussin(g, K, x, 1, 12, 9);
  g.rect(6, 10, 36, 6, K.s); g.rect(6, 16, 36, 2, K.d);
  for (const x of [6, 24]) { g.rect(x, 10, 18, 2, K.hi); g.rect(x, 12, 18, 4, K.b); g.rect(x, 15, 18, 1, K.s); g.px(x, 10, K.b); }
  g.rect(23, 10, 1, 6, K.d); g.rect(41, 11, 1, 5, K.s);
  const k = s.L(), Ks = R("coussin");
  comCoussin(k, Ks, 8, 4, 8, 7, false); k.px(9, 5, Ks.hi); k.line(10, 7, 13, 7, Ks.s);
  const a = s.L();
  for (const x of [0, 42]) {
    a.rect(x, 6, 6, 12, K.b); a.rect(x, 6, 6, 2, K.hi); a.rect(x, 6, 1, 11, K.hi); a.rect(x + 5, 8, 1, 10, K.s);
    a.rect(x + 1, 8, 5, 1, K.s); a.rect(x, 17, 6, 1, K.d); a.clr(x, 6); a.clr(x + 5, 6);
  }
  for (const x of [2, 44]) { a.rect(x, 18, 2, 2, W.s); a.px(x, 18, W.b); }
  return s;
}
function comFrigo() {
  const s = mk(20, 36), g = s.L(), F = R("frigo"), M = P.metal;
  g.rect(0, 0, 20, 36, F.s); g.rect(0, 0, 20, 1, F.b); g.rect(0, 0, 1, 34, F.b);
  const porte = (y, h) => { g.rect(2, y, 16, h, F.b); g.rect(2, y, 16, 1, F.hi); g.rect(2, y, 2, h - 1, F.hi); g.rect(17, y + 1, 1, h - 1, F.s); g.rect(3, y + h - 1, 15, 1, F.s); };
  porte(2, 10); porte(14, 19);
  g.rect(1, 12, 18, 2, F.d);
  for (const [y, h] of [[4, 5], [16, 7]]) { g.rect(14, y, 2, h, M.b); g.rect(14, y, 1, h, M.hi); g.rect(15, y + 1, 1, h - 1, M.s); g.px(16, y + 1, F.s); g.px(16, y + h - 1, F.s); }
  g.rect(1, 33, 18, 3, F.d); for (let x = 4; x < 16; x += 2) g.px(x, 34, F.s);
  const n = s.L(), Y = R("postit");
  n.rect(5, 18, 6, 6, Y.b); n.rect(5, 18, 6, 1, Y.hi); n.rect(10, 19, 1, 5, Y.s); n.px(10, 23, Y.d);
  n.line(6, 20, 9, 20, Y.d); n.line(6, 22, 8, 22, Y.d);
  n.rect(7, 17, 2, 2, "livre1.b"); n.px(7, 17, "livre1.hi");
  return s;
}
function comClasseur() {
  const s = mk(20, 32), g = s.L(), K = R("classeur"), M = P.metal, T = R("etiquette");
  g.rect(0, 0, 20, 30, K.s); g.rect(0, 0, 20, 1, K.hi); g.rect(0, 0, 1, 30, K.b); g.rect(19, 1, 1, 29, K.d);
  for (const y of [2, 11, 20]) {
    g.rect(2, y, 16, 8, K.b); g.rect(2, y, 16, 1, K.hi); g.rect(2, y, 1, 7, K.hi); g.rect(17, y + 1, 1, 7, K.s); g.rect(2, y + 7, 16, 1, K.d);
    g.rect(7, y + 2, 6, 2, M.s); g.rect(8, y + 2, 4, 2, T.b); g.px(8, y + 2, T.hi); g.px(11, y + 3, T.s);
    g.rect(7, y + 5, 6, 1, M.hi); g.rect(8, y + 6, 4, 1, M.s);
  }
  g.rect(1, 30, 3, 2, K.d); g.rect(16, 30, 3, 2, K.d);
  return s;
}
function comTableReunion() {
  const s = mk(48, 24), W = P.wood, Ch = P.chair;
  const c = s.L();
  for (const x of [0, 46]) { c.rect(x, 6, 2, 8, Ch.b); c.rect(x, 6, 2, 1, Ch.hi); c.rect(x + 1, 7, 1, 7, Ch.s); }
  const g = s.L();
  g.rect(4, 4, 40, 10, W.b); g.rect(4, 4, 40, 1, W.hi); g.rect(4, 4, 1, 10, W.hi);
  [[8, 6, 12], [24, 6, 9], [12, 8, 7], [27, 9, 13], [6, 11, 10], [21, 11, 6], [35, 7, 6]].forEach(([x, y, w]) => g.rect(x, y, w, 1, W.s));
  g.px(30, 9, W.d); g.px(14, 6, W.hi); g.px(38, 11, W.hi);
  g.rect(4, 14, 40, 2, W.s); g.rect(4, 15, 40, 1, W.d);
  for (const x of [8, 36]) { g.rect(x, 16, 4, 8, W.s); g.rect(x, 16, 1, 8, W.b); g.rect(x, 16, 4, 1, W.d); }
  return s;
}
function comChaise() {
  const s = mk(16, 20), g = s.L(), W = P.wood;
  g.rect(2, 0, 12, 3, W.b); g.rect(2, 0, 12, 1, W.hi); g.rect(3, 2, 11, 1, W.s);
  for (const x of [2, 12]) { g.rect(x, 1, 2, 9, W.b); g.rect(x, 1, 1, 9, W.hi); g.px(x + 1, 9, W.s); }
  g.rect(13, 1, 1, 9, W.s);
  for (const x of [6, 9]) { g.rect(x, 3, 2, 7, W.s); g.px(x, 3, W.b); }
  g.rect(4, 6, 8, 1, W.b); g.rect(4, 7, 8, 1, W.d);
  g.rect(0, 10, 16, 4, W.b); g.rect(0, 10, 16, 1, W.hi); g.rect(0, 12, 16, 2, W.s); g.rect(1, 13, 15, 1, W.d); g.clr(0, 10); g.clr(15, 10);
  for (const x of [2, 12]) { g.rect(x, 14, 2, 6, W.s); g.px(x, 14, W.d); g.rect(x, 15, 1, 5, W.b); }
  return s;
}
/** Le bureau en bois : fauteuil derrière, la figure de la salle assise, plateau veiné, caisson à deux tiroirs. */
function comBureauEnBois({ qui = "directeur", vide = false } = {}) {
  const s = mk(32, 36), F = COM_FIGURES[qui], Ch = P.chair, W = P.wood, M = P.metal;
  const ch = s.L();
  ch.rect(7, 9, 18, 15, Ch.b); ch.rect(7, 9, 18, 1, Ch.hi); ch.rect(7, 9, 1, 15, Ch.hi); ch.rect(24, 10, 1, 14, Ch.s);
  ch.clr(7, 9); ch.clr(24, 9); ch.px(11, 13, Ch.d); ch.px(20, 13, Ch.d); ch.px(11, 18, Ch.d); ch.px(20, 18, Ch.d);
  if (vide) { ch.rect(6, 19, 20, 5, Ch.s); ch.rect(6, 19, 20, 1, Ch.hi); ch.rect(6, 20, 20, 2, Ch.b); }
  const g = s.L(), a = s.L();
  if (!vide) {
    const T = P.top[F.haut], K = P.skin[F.ph.peau - 1];
    tete(g, 10, 6, F.ph);
    g.rect(14, 15, 4, 1, K.s);
    g.rect(9, 16, 14, 8, T.b); g.rect(8, 17, 16, 7, T.b); g.rect(20, 17, 4, 7, T.s); g.rect(9, 17, 4, 1, T.hi); g.px(9, 18, T.hi);
    if (F.cravate) {
      g.rect(13, 16, 6, 1, P.col.b); g.px(13, 17, P.col.b); g.px(14, 17, P.col.b); g.px(17, 17, P.col.s); g.px(18, 17, P.col.s);
      g.rect(15, 16, 2, 1, P.cravate.hi); g.rect(15, 17, 2, 5, P.cravate.b); g.px(15, 17, P.cravate.hi); g.px(16, 22, P.cravate.b);
      g.line(13, 18, 14, 21, T.s); g.line(18, 18, 17, 21, T.d);
    } else {
      g.rect(13, 16, 2, 2, P.col.b); g.rect(17, 16, 2, 2, P.col.s); g.rect(15, 16, 2, 1, K.s);
      [19, 21].forEach(y => g.px(16, y, T.d));
    }
    a.rect(6, 18, 3, 5, T.s); a.rect(6, 18, 1, 4, T.d); a.rect(23, 18, 3, 5, T.s);
    a.rect(7, 22, 4, 2, K.b); a.px(10, 23, K.s); a.rect(21, 22, 4, 2, K.b); a.px(21, 23, K.s);
  }
  const d = s.L();
  d.rect(27, 21, 3, 3, M.b); d.px(27, 21, M.hi); d.rect(29, 21, 1, 3, M.s);
  d.rect(27, 18, 1, 3, P.books[0].b); d.rect(29, 19, 1, 2, P.books[1].b); d.px(28, 20, P.books[2].b);
  d.rect(2, 24, 28, 1, W.hi); d.rect(2, 25, 28, 3, W.b);
  [[4, 26, 7], [15, 25, 6], [22, 26, 5], [12, 27, 4]].forEach(([x, y, w]) => d.rect(x, y, w, 1, W.s));
  d.rect(2, 28, 28, 2, W.s); d.rect(2, 29, 28, 1, W.d);
  d.rect(4, 30, 2, 6, W.s); d.rect(4, 30, 1, 6, W.b);
  d.rect(19, 30, 9, 6, W.b); d.rect(19, 30, 9, 1, W.d); d.rect(27, 31, 1, 5, W.s); d.rect(19, 33, 9, 1, W.s); d.rect(19, 31, 1, 5, W.hi);
  d.rect(22, 31, 3, 1, M.hi); d.rect(22, 34, 3, 1, M.hi);
  return s;
}
/** Les lignes de l'écran allumé, en motif répété : six lignes, une rangée sur deux. */
const COM_LIGNES = [6, 4, 6, 3, 5, 6];
/** La console : écran sur pied, façade de métal, rangée de touches. Allumé, quatre images font défiler le texte. */
function comConsole({ allume = true } = {}) {
  const s = mk(40, 36), M = P.metal, Fr = P.frame, L = E("actif");
  const g = s.L();
  g.rect(30, 18, 4, 5, M.s); g.rect(30, 18, 1, 5, M.b); g.rect(28, 22, 8, 2, M.b); g.rect(28, 22, 8, 1, M.hi);
  g.rect(26, 6, 12, 12, Fr.b); g.rect(26, 6, 12, 1, Fr.hi); g.rect(26, 7, 1, 10, Fr.hi); g.rect(37, 7, 1, 11, Fr.s); g.rect(27, 17, 10, 1, Fr.s);
  if (allume) g.rect(28, 8, 8, 8, L.d);
  else { g.rect(28, 8, 8, 8, Fr.d); g.line(29, 11, 31, 9, Fr.s); g.px(29, 12, Fr.s); }
  g.rect(2, 24, 36, 1, M.hi); g.rect(2, 25, 36, 3, M.b); g.rect(2, 25, 1, 3, M.hi);
  for (let x = 8; x <= 28; x += 4) { g.rect(x, 25, 2, 2, P.clavier.b); g.px(x, 25, P.clavier.hi); g.px(x + 1, 26, P.clavier.s); }
  g.rect(2, 28, 36, 2, M.s); g.rect(2, 29, 36, 1, M.d); for (let x = 12; x < 28; x += 2) g.px(x, 28, M.d);
  for (const x of [4, 34]) { g.rect(x, 30, 2, 6, M.b); g.rect(x + 1, 30, 1, 6, M.s); g.px(x, 30, M.d); }
  if (allume) for (let k = 0; k < 4; k++) {
    const f = s.L(`com-ecran com-f${k}`, `animation-delay:${k * .3}s`);
    for (let i = 0; i < 8; i++) {
      const y = 9 + 2 * i - 2 * k;
      if (y < 9 || y > 14) continue;
      const w = COM_LIGNES[i % COM_LIGNES.length];
      f.rect(29, y, w, 1, L.b); f.px(29, y, L.hi);
      if (w > 4) f.px(29 + w - 1, y, L.hi);
    }
  }
  return s;
}

enregistrer({ id: "com-canape", nom: "Canapé", fichier: "Canape", salle: "communs", grille: "24 × 10 → 48 × 20", dw: 72, dh: 30,
  avant: () => avantCanape(), apres: () => comCanape(),
  note: "Trois coussins de dossier capitonnés, deux d'assise, des accoudoirs arrondis, des pieds en bois et un coussin moutarde posé à gauche." });
enregistrer({ id: "com-frigo", nom: "Réfrigérateur", fichier: "Frigo", salle: "communs", grille: "10 × 18 → 20 × 36", dw: 30, dh: 54,
  avant: () => avantFrigo(), apres: () => comFrigo(),
  note: "Deux portes en relief, des poignées en métal, une grille d'aération en bas, et un post-it tenu par un aimant." });
enregistrer({ id: "com-classeur", nom: "Classeur à tiroirs", fichier: "Classeur", salle: "communs", grille: "10 × 16 → 20 × 32", dw: 30, dh: 48,
  avant: () => avantClasseur(), apres: () => comClasseur(),
  note: "Chaque tiroir a son porte-étiquette et sa poignée en métal ; le meuble pose sur deux patins." });
enregistrer({ id: "com-table-reunion", nom: "Table de réunion", fichier: "TableDeReunion", salle: "communs", grille: "24 × 12 → 48 × 24", dw: 72, dh: 36,
  avant: () => avantTableReunion(), apres: () => comTableReunion(),
  note: "Le plateau a un veinage, un chant épais et des pieds massifs. Les dossiers aux deux bouts restent ceux des chaises. Rien sur la table : la salle se lit à ses occupants." });
enregistrer({ id: "com-chaise", nom: "Chaise de réunion", fichier: "Chaise", salle: "communs", grille: "8 × 10 → 16 × 20", dw: 24, dh: 30,
  avant: () => avantChaise(), apres: () => comChaise(),
  note: "Une vraie chaise en bois : dossier à barreaux, traverse, assise épaisse, quatre pieds dont deux visibles." });
enregistrer({ id: "com-bureau-directeur", nom: "Bureau du directeur", fichier: "BureauEnBois", salle: "communs", grille: "16 × 18 → 32 × 36", dw: 56, dh: 63,
  avant: () => avantBureauEnBois("directeur"), apres: () => comBureauEnBois({ qui: "directeur" }),
  variante: { label: "En visite (vide)", f: () => comBureauEnBois({ qui: "directeur", vide: true }) },
  note: "Le directeur en costume, chemise et cravate, dans un fauteuil capitonné. Le bureau gagne un plateau veiné, un caisson à deux tiroirs et un pot à crayons. En visite, le fauteuil reste vide." });
enregistrer({ id: "com-bureau-rh", nom: "Bureau des RH", fichier: "BureauEnBois", salle: "communs", grille: "16 × 18 → 32 × 36", dw: 56, dh: 63,
  avant: () => avantBureauEnBois("rh"), apres: () => comBureauEnBois({ qui: "rh" }),
  note: "La recruteuse en gilet sur un col de chemise, mains posées sur le même bureau en bois que le directeur." });
enregistrer({ id: "com-console", nom: "Console allumée", fichier: "Console", salle: "communs", grille: "20 × 18 → 40 × 36", dw: 70, dh: 63,
  avant: () => avantConsole(true), apres: () => comConsole({ allume: true }),
  note: "Un vrai moniteur sur pied, des touches en relief sur le pupitre, une façade à fentes. Le texte défile en quatre images ; il s'arrête sous « mouvement réduit »." });
enregistrer({ id: "com-console-eteinte", nom: "Console éteinte", fichier: "Console", salle: "communs", grille: "20 × 18 → 40 × 36", dw: 70, dh: 63,
  avant: () => avantConsole(false), apres: () => comConsole({ allume: false }),
  note: "Éteint, l'écran est noir avec un reflet : aucune couleur d'état, rien ne bouge." });
