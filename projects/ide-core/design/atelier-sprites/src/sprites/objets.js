"use strict";
/*
 * Les objets de la pièce de run : imprimante sur son meuble, dossier de la pile,
 * corbeille, boîte aux lettres, gyrophare, vapeur du café, confettis. Grille ×2.
 * Seuls le drapeau de la boîte et le gyrophare portent un état (ADR-058) : jetons E().
 */

/* ---------- Couleurs d'aujourd'hui qui manquaient aux copies fidèles ---------- */
Object.assign(C, {
  classeur: "#71717a", classeurO: "#52525b", feuille: "#f4f4f5",
  dossier: "#ca8a04", dossierO: "#a16207",
  corbeille: "#52525b", corbeilleO: "#3f3f46", papier: "#f4f4f5", papierO: "#a1a1aa",
  gyro: "#dc2626", gyroClair: "#fca5a5", gyroSocle: "#3f3f46",
  vapeur: "#d4d4d8",
  confetti: ["#f43f5e", "#facc15", "#22d3ee", "#a3e635", "#e879f9"],
});

/* ---------- Familles nouvelles : tessera = teinte actuelle, chaud, neon (nuit) ---------- */
Object.assign(FAMILLES, {
  imprimante: { tessera: "#71717a", chaud: "#9c9384", neon: "#3a3f66" },
  papier: { tessera: "#f4f4f5", chaud: "#f3ecdc", neon: "#d6dbff" },
  dossier: { tessera: "#ca8a04", chaud: "#d9a040", neon: "#ffb13d" },
  boite: { tessera: "#52525b", chaud: "#9a4a32", neon: "#3a2f6a" },
  vapeur: { tessera: "#d4d4d8", chaud: "#ece4d6", neon: "#bfc8ff" },
  confetti1: { tessera: "#f43f5e", chaud: "#f0603e", neon: "#ff2d75" },
  confetti2: { tessera: "#facc15", chaud: "#f5b82e", neon: "#ffe14d" },
  confetti3: { tessera: "#22d3ee", chaud: "#3cc4b4", neon: "#2df5ff" },
  confetti4: { tessera: "#a3e635", chaud: "#b5d43a", neon: "#9dff3d" },
  confetti5: { tessera: "#e879f9", chaud: "#e07ab8", neon: "#ff4dff" },
});

/* ---------- Copies fidèles ---------- */
function avantImprimante() {
  const s = mk(24, 14), g = s.L();
  g.rect(1, 2, 9, 4, C.classeur); g.rect(2, 0, 7, 2, C.classeurO); g.rect(3, 4, 5, 1, C.feuille);
  g.rect(0, 6, 24, 2, C.table); g.rect(1, 8, 22, 6, C.tableO); g.rect(11, 10, 2, 1, C.table);
  return s;
}
function avantDossier() {
  const s = mk(10, 8), g = s.L();
  g.rect(0, 0, 4, 2, C.dossierO); g.rect(0, 1, 10, 7, C.dossier); g.rect(0, 7, 10, 1, C.dossierO);
  return s;
}
const PLACES_BOULES_AVANT = [[1, 1], [5, 1], [3, 0]];
function avantCorbeille(boules = 0) {
  const s = mk(10, 12), g = s.L();
  for (const [x, y] of PLACES_BOULES_AVANT.slice(0, boules)) {
    g.rect(x, y + 2, 3, 3, C.papier); g.rect(x + 1, y + 1, 2, 1, C.papier); g.rect(x + 2, y + 4, 1, 1, C.papierO);
  }
  g.rect(0, 5, 10, 1, C.corbeilleO); g.rect(1, 6, 8, 6, C.corbeille);
  g.rect(3, 7, 1, 4, C.corbeilleO); g.rect(6, 7, 1, 4, C.corbeilleO);
  return s;
}
const DRAPEAU_AVANT = { ouverte: ETAT_AVANT.question, ci: ETAT_AVANT.actif, mergee: ETAT_AVANT.fait, refusee: ETAT_AVANT.blocage };
function avantBoite(etat = "ci") {
  const s = mk(12, 12), g = s.L();
  g.rect(5, 8, 2, 4, C.z700); g.rect(1, 3, 9, 5, C.z600); g.rect(2, 4, 5, 1, C.z800);
  if (etat !== "aucune") { g.rect(10, 1, 1, 5, DRAPEAU_AVANT[etat]); g.rect(8, 1, 2, 2, DRAPEAU_AVANT[etat]); }
  return s;
}
function avantGyrophare() {
  const s = mk(10, 8), d = s.L("anim-obj-gyro");
  d.rect(2, 1, 6, 4, C.gyro); d.rect(3, 0, 4, 1, C.gyro); d.rect(4, 2, 2, 2, C.gyroClair);
  s.L().rect(1, 5, 8, 3, C.gyroSocle);
  return s;
}
function avantVapeur() {
  const s = mk(12, 8), g = s.L("anim-obj-vapeur");
  g.rect(3, 4, 1, 3, C.vapeur); g.rect(5, 1, 1, 4, C.vapeur); g.rect(8, 3, 1, 3, C.vapeur);
  return s;
}
/** Cinq confettis d'échantillon, un par ton : 2 × 3 unités chacun (4 × 6 px dans Tessera). */
const CONFETTIS = [[1, 1], [5, 4], [9, 0], [13, 3], [17, 2]];
function avantConfettis() {
  const s = mk(20, 8);
  CONFETTIS.forEach(([x, y], i) => s.L("anim-obj-chute", `animation-delay:-${(i % 6) * .25}s`).rect(x, y, 2, 3, C.confetti[i]));
  return s;
}

/* ---------- Grille ×2, en jetons ---------- */

/** Le meuble bas et son imprimante, 48 × 28 : bac d'entrée, feuille imprimée, deux portes. */
function objImprimante() {
  const s = mk(48, 28), g = s.L(), I = R("imprimante"), Pa = R("papier"), W = P.wood, M = P.metal;
  // Bac d'alimentation et sa ramette, derrière le corps
  g.rect(6, 0, 10, 2, Pa.b); g.rect(6, 0, 10, 1, Pa.hi); g.rect(15, 1, 1, 1, Pa.s);
  g.rect(4, 1, 14, 3, I.s); g.rect(4, 1, 14, 1, I.b); g.rect(5, 2, 12, 1, I.d);
  // Corps : arête éclairée en haut à gauche, flanc droit dans l'ombre
  g.rect(2, 4, 18, 8, I.b); g.rect(2, 4, 18, 1, I.hi); g.rect(2, 4, 1, 8, I.hi); g.rect(18, 5, 2, 7, I.s); g.rect(3, 11, 17, 1, I.s);
  // Panneau : petit afficheur éteint et deux touches (aucun voyant : l'imprimante ne rend aucun état)
  g.rect(14, 6, 4, 1, P.frame.d); g.rect(14, 7, 4, 1, I.hi); g.px(14, 9, I.d); g.px(16, 9, I.d);
  // Fente de sortie et feuille imprimée
  g.rect(4, 7, 9, 1, I.d);
  g.rect(5, 8, 7, 3, Pa.b); g.rect(5, 8, 7, 1, Pa.hi); g.rect(6, 9, 4, 1, Pa.s); g.rect(6, 10, 3, 1, Pa.s); g.rect(11, 9, 1, 2, Pa.s);
  // Le dessus du meuble : chant éclairé, épaisseur
  g.rect(0, 12, 48, 4, W.b); g.rect(0, 12, 48, 1, W.hi); g.rect(0, 15, 48, 1, W.s);
  // Le caisson et ses deux portes
  g.rect(2, 16, 44, 12, W.s); g.rect(2, 16, 44, 1, W.d);
  for (const x of [4, 25]) {
    g.rect(x, 18, 19, 9, W.b); g.rect(x, 18, 19, 1, W.hi); g.rect(x, 18, 1, 9, W.hi); g.rect(x + 18, 19, 1, 8, W.s); g.rect(x + 1, 26, 18, 1, W.s);
  }
  g.rect(21, 21, 1, 3, M.hi); g.px(21, 23, M.s); g.rect(26, 21, 1, 3, M.hi); g.px(26, 23, M.s);
  g.rect(2, 27, 44, 1, W.d);
  return s;
}

/** Un dossier de la pile, 20 × 16 : onglet, feuilles qui dépassent, étiquette. */
function objDossier() {
  const s = mk(20, 16), g = s.L(), D = R("dossier"), Pa = R("papier");
  // Le dos du dossier et son onglet
  g.rect(0, 0, 8, 3, D.s); g.rect(0, 0, 7, 1, D.b); g.rect(0, 2, 20, 4, D.s);
  // Deux feuilles qui dépassent, décalées
  g.rect(3, 2, 15, 3, Pa.s); g.rect(2, 3, 15, 2, Pa.b); g.rect(2, 3, 15, 1, Pa.hi);
  // Le rabat avant
  g.rect(0, 5, 20, 11, D.b); g.rect(0, 5, 20, 1, D.hi); g.rect(0, 5, 1, 10, D.hi); g.rect(19, 6, 1, 10, D.s); g.rect(0, 15, 20, 1, D.d);
  // L'étiquette du ticket
  g.rect(3, 8, 9, 4, Pa.b); g.rect(3, 8, 9, 1, Pa.hi); g.rect(4, 9, 6, 1, Pa.s); g.rect(4, 10, 4, 1, Pa.s); g.rect(11, 9, 1, 3, Pa.s);
  return s;
}

/** Une boule de papier froissé, 6 × 6 : plis en creux, éclairée en haut à gauche. */
function objBoule(g, x, y) {
  const Pa = R("papier");
  g.stamp(x, y, [
    ".hhb..",
    "hhbsb.",
    "hbsbbs",
    "bbbsbs",
    ".bsbss",
    "..sss.",
  ], { h: Pa.hi, b: Pa.b, s: Pa.s });
}
/** Où se pose chaque boule, ×2 : les deux de devant, puis celle du dessus. */
const PLACES_BOULES = [[2, 4], [10, 4], [6, 2]];
/** La corbeille, 20 × 24 : seau perforé qui s'affine, rebord roulé ; une boule par refus du reviewer. */
function objCorbeille(boules = 0) {
  const s = mk(20, 24), M = P.metal;
  const b = s.L();
  // La boule du dessus d'abord : celles de devant la recouvrent
  const ordre = PLACES_BOULES.slice(0, boules);
  [...ordre.slice(2), ...ordre.slice(0, 2)].forEach(([x, y]) => objBoule(b, x, y));
  const g = s.L();
  for (let y = 12; y < 24; y++) {
    const i = y >= 18 ? 3 : 2;
    g.rect(i, y, 20 - 2 * i, 1, M.b); g.px(i, y, M.hi); g.rect(19 - i - 1, y, 2, 1, M.s);
  }
  g.rect(2, 12, 16, 1, M.d);
  for (const y of [14, 17, 20]) for (let x = 5; x < 16; x += 3) g.px(x + (y === 17 ? 1 : 0), y, M.d);
  g.rect(3, 23, 14, 1, M.d);
  g.rect(0, 10, 20, 2, M.b); g.rect(0, 10, 20, 1, M.hi); g.rect(18, 11, 2, 1, M.s);
  return s;
}

/** Le drapeau de la boîte, par état de la PR : jamais une famille thémée. */
const DRAPEAU = { ouverte: "question", ci: "actif", mergee: "fait", refusee: "blocage" };
/** La boîte aux lettres, 24 × 24 : dos arrondi, porte et fente ; le drapeau se lève s'il y a une PR. */
function objBoite(etat = "ci") {
  const s = mk(24, 24), g = s.L(), B = R("boite"), M = P.metal, Pa = R("papier");
  // Deux touffes d'herbe au pied du poteau
  g.stamp(7, 20, ["b.b", "bbb"], { b: P.plant.s }); g.stamp(15, 20, [".b.", "bbs"], { b: P.plant.s, s: P.plant.d });
  // Le poteau et sa platine
  g.rect(10, 16, 4, 8, M.b); g.rect(10, 16, 1, 8, M.hi); g.rect(13, 16, 1, 8, M.s); g.rect(10, 16, 4, 1, M.d);
  // Le corps, bombé sur le dessus
  g.rect(4, 6, 14, 1, B.b); g.rect(3, 7, 16, 1, B.b); g.rect(2, 8, 18, 8, B.b);
  g.rect(4, 6, 12, 1, B.hi); g.rect(3, 7, 2, 1, B.hi); g.rect(2, 8, 1, 7, B.hi);
  g.rect(18, 8, 2, 8, B.s); g.rect(3, 15, 17, 1, B.d);
  // La porte, à gauche, et sa poignée
  g.rect(4, 8, 1, 7, B.s); g.rect(3, 11, 1, 2, M.hi);
  // La fente : une lettre y dépasse tant qu'une PR existe
  if (etat !== "aucune") { g.rect(8, 8, 6, 2, Pa.b); g.rect(8, 8, 6, 1, Pa.hi); g.px(13, 9, Pa.s); }
  g.rect(7, 10, 9, 1, B.d); g.rect(7, 11, 9, 1, B.hi);
  // Le pivot du drapeau
  g.rect(20, 10, 2, 2, M.s); g.px(20, 10, M.hi);
  if (etat !== "aucune") {
    const L = E(DRAPEAU[etat]), d = s.L();
    d.rect(20, 2, 2, 9, L.s); d.rect(20, 2, 1, 9, L.b);
    d.rect(15, 2, 5, 4, L.b); d.rect(15, 2, 5, 1, L.hi); d.rect(15, 5, 5, 1, L.s);
  }
  return s;
}

/** Le gyrophare, 20 × 16 : dôme strié et lampe en jetons d'état (blocage), socle vissé. Le dôme et ses éclats clignotent. */
function objGyrophare() {
  const s = mk(20, 16), L = E("blocage"), M = P.metal;
  const d = s.L("anim-obj-gyro");
  d.rect(7, 0, 6, 1, L.s); d.rect(6, 1, 8, 1, L.b);
  d.rect(5, 2, 10, 8, L.b); d.rect(5, 2, 1, 8, L.hi); d.rect(13, 2, 2, 8, L.s);
  for (const x of [7, 11]) d.rect(x, 3, 1, 7, L.s);
  d.rect(8, 3, 3, 4, L.hi); d.px(9, 4, L.hi);
  // Les éclats, de part et d'autre du dôme
  d.rect(1, 5, 2, 1, L.hi); d.px(2, 2, L.b); d.px(3, 3, L.b); d.rect(17, 5, 2, 1, L.hi); d.px(17, 2, L.b); d.px(16, 3, L.b);
  const g = s.L();
  g.rect(4, 10, 12, 1, M.d);
  g.rect(3, 11, 14, 5, M.b); g.rect(3, 11, 14, 1, M.hi); g.rect(3, 11, 1, 5, M.hi); g.rect(15, 12, 2, 4, M.s); g.rect(4, 15, 13, 1, M.d);
  g.px(5, 13, M.d); g.px(14, 13, M.d);
  return s;
}

/** Trois volutes en S, fines en haut, plus denses en bas, qui montent chacune à son rythme. */
const VOLUTE = ["..h.", ".h..", ".b..", ".bb.", "..bb", "..bb", ".bb.", ".bs.", "bs.."];
const VOLUTE_HAUTE = [".h..", "h...", "b...", "bb..", ".bb.", "..bb", "..bb", ".bb.", ".bs.", "bs.."];
const miroir = rows => rows.map(r => [...r].reverse().join(""));
function objVapeur() {
  const s = mk(24, 16), V = R("vapeur"), map = { h: V.hi, b: V.b, s: V.s };
  s.L("anim-obj-vapeur", "animation-delay:-.4s").stamp(5, 6, VOLUTE, map);
  s.L("anim-obj-vapeur").stamp(9, 1, VOLUTE_HAUTE, map);
  s.L("anim-obj-vapeur", "animation-delay:-.9s").stamp(15, 4, miroir(VOLUTE), map);
  return s;
}

/** Les cinq confettis, 4 × 6 chacun : à plat, incliné, en lanière, de chant, penché. */
const FORMES_CONFETTI = [
  ["hhbb", "hbbs", "hbbs", "hbbs", "hbbs", "bbss"],
  ["hb..", "hbb.", "bbbs", ".bbs", "..bs", "...s"],
  ["...h", "..hb", "..bs", ".bs.", ".bs.", "bs.."],
  [".hb.", ".hb.", ".bs.", ".bs.", ".bs.", ".ss."],
  ["..hb", ".hbb", "hbbs", "bbs.", "bs..", "s..."],
];
function objConfettis() {
  const s = mk(40, 16);
  CONFETTIS.forEach(([x, y], i) => {
    const K = R("confetti" + (i + 1));
    s.L("anim-obj-chute", `animation-delay:-${(i % 6) * .25}s`).stamp(x * 2, y * 2, FORMES_CONFETTI[i], { h: K.hi, b: K.b, s: K.s });
  });
  return s;
}

/* ---------- Registre ---------- */
enregistrer({ id: "obj-imprimante", nom: "Imprimante sur son meuble", fichier: "Imprimante", salle: "run", grille: "24 × 14 → 48 × 28", dw: 72, dh: 42,
  avant: () => avantImprimante(), apres: () => objImprimante(),
  note: "Une vraie imprimante : ramette dans le bac, feuille imprimée qui sort, petit afficheur éteint. Le meuble gagne deux portes et leurs poignées. Toujours aucun voyant." });
enregistrer({ id: "obj-dossier", nom: "Dossier de la pile", fichier: "Dossier", salle: "run", grille: "10 × 8 → 20 × 16", dw: 20, dh: 16,
  avant: () => avantDossier(), apres: () => objDossier(),
  note: "Un dossier en carton avec son onglet, deux feuilles qui dépassent et une étiquette de ticket sur le rabat." });
enregistrer({ id: "obj-corbeille-vide", nom: "Corbeille vide", fichier: "Corbeille (boules = 0)", salle: "run", grille: "10 × 12 → 20 × 24", dw: 20, dh: 24,
  avant: () => avantCorbeille(0), apres: () => objCorbeille(0),
  note: "Un seau en métal perforé qui s'affine vers le bas, avec un rebord roulé : on voit que c'est une corbeille même vide." });
enregistrer({ id: "obj-corbeille-pleine", nom: "Corbeille, trois refus", fichier: "Corbeille (boules = 3)", salle: "run", grille: "10 × 12 → 20 × 24", dw: 20, dh: 24,
  avant: () => avantCorbeille(3), apres: () => objCorbeille(3), variante: { label: "Un refus", f: () => objCorbeille(1) },
  note: "Chaque refus du reviewer devient une vraie boule de papier froissé, avec ses plis ; elles s'empilent au-dessus du rebord." });
enregistrer({ id: "obj-boite-ci", nom: "Boîte aux lettres, CI en cours", fichier: "Boite (etat = ci)", salle: "run", grille: "12 × 12 → 24 × 24", dw: 36, dh: 36,
  avant: () => avantBoite("ci"), apres: () => objBoite("ci"), variante: { label: "Aucune PR", f: () => objBoite("aucune") },
  note: "Une boîte bombée avec porte, fente et poteau. Le drapeau garde la couleur de l'état ; une lettre dépasse de la fente tant qu'une PR existe. Sans PR : ni drapeau, ni lettre." });
enregistrer({ id: "obj-boite-ouverte", nom: "Boîte aux lettres, PR ouverte", fichier: "Boite (etat = ouverte)", salle: "run", grille: "12 × 12 → 24 × 24", dw: 36, dh: 36,
  avant: () => avantBoite("ouverte"), apres: () => objBoite("ouverte"),
  note: "Drapeau ambre : la PR attend qu'un humain la merge." });
enregistrer({ id: "obj-boite-mergee", nom: "Boîte aux lettres, PR mergée", fichier: "Boite (etat = mergee)", salle: "run", grille: "12 × 12 → 24 × 24", dw: 36, dh: 36,
  avant: () => avantBoite("mergee"), apres: () => objBoite("mergee"),
  note: "Drapeau vert : la PR est mergée." });
enregistrer({ id: "obj-boite-refusee", nom: "Boîte aux lettres, PR refusée", fichier: "Boite (etat = refusee)", salle: "run", grille: "12 × 12 → 24 × 24", dw: 36, dh: 36,
  avant: () => avantBoite("refusee"), apres: () => objBoite("refusee"),
  note: "Drapeau rouge : le watcher n'a pas mergé la PR." });
enregistrer({ id: "obj-gyrophare", nom: "Gyrophare, CI rouge", fichier: "Gyrophare", salle: "run", grille: "10 × 8 → 20 × 16", dw: 30, dh: 24,
  avant: () => avantGyrophare(), apres: () => objGyrophare(),
  note: "Un dôme strié avec sa lampe au centre et des éclats de part et d'autre, qui clignotent ensemble ; le socle en métal vissé reste fixe. Le rouge vient de l'état blocage." });
enregistrer({ id: "obj-vapeur", nom: "Vapeur du café", fichier: "Vapeur", salle: "run", grille: "12 × 8 → 24 × 16", dw: 36, dh: 24,
  avant: () => avantVapeur(), apres: () => objVapeur(),
  note: "Trois traits deviennent trois volutes en S, chacune décalée dans sa montée." });
enregistrer({ id: "obj-confettis", nom: "Confettis d'une PR mergée", fichier: "Confettis (échantillon de cinq)", salle: "run", grille: "20 × 8 → 40 × 16", dw: 40, dh: 16,
  avant: () => avantConfettis(), apres: () => objConfettis(),
  note: "Chaque confetti tourne sur lui-même : à plat, incliné, en lanière, vu de chant. Toujours cinq tons, 4 × 6 px." });
