"use strict";
/*
 * Le mur de la pièce de run : fenêtre, plafonnier, tableau blanc, horloge, cadres,
 * porte, interrupteur, étagère. Grille ×2. Seul le tableau blanc porte des états
 * (ADR-058) ; le ciel et l'heure sont des données, pas des états.
 */

Object.assign(C, {
  fenetreCadre: "#52525b", cielJour: "#7dd3fc", cielNuit: "#1e1b4b", soleil: "#fde047", nuage: "#f4f4f5", etoile: "#e4e4e7",
  plafonnier: "#fde68a", cadreFond: "#27272a", tableau: "#e4e4e7", tableauCadre: "#52525b", tableauCase: "#a1a1aa",
  vert500: "#22c55e", rouge500: "#ef4444", horlogeBord: "#52525b", horlogeCadran: "#e4e4e7", horlogeAiguille: "#27272a",
  cadreBois: "#8a6a4a", toiles: ["#7dd3fc", "#4d7c0f", "#fde047", "#be185d"], cadreDore: "#ca8a04",
  porte: "#6b5038", porteOmbre: "#4a3626", interrupteur: "#d4d4d8", interrupteurTouche: "#71717a", etagere: "#6b5038",
});

Object.assign(FAMILLES, {
  fenetre: { tessera: "#52525b", chaud: "#e6dcc6", neon: "#2d3150" },
  ciel: { tessera: "#7dd3fc", chaud: "#8ccbe8", neon: "#3a7bd5" },
  "ciel-nuit": { tessera: "#1e1b4b", chaud: "#26204f", neon: "#0d0b2e" },
  soleil: { tessera: "#fde047", chaud: "#fcc83a", neon: "#ffd23d" },
  nuage: { tessera: "#f4f4f5", chaud: "#fbf3e6", neon: "#b9c2ff" },
  etoile: { tessera: "#e4e4e7", chaud: "#fff4d6", neon: "#fff3a8" },
  lampe: { tessera: "#fde68a", chaud: "#ffd98a", neon: "#ffe36b" },
  tableau: { tessera: "#e4e4e7", chaud: "#f0ebdd", neon: "#aeb4e6" },
  cadran: { tessera: "#e4e4e7", chaud: "#f2e8d0", neon: "#c7ccff" },
  toile1: { tessera: "#7dd3fc", chaud: "#8cc8e0", neon: "#3dd6ff" },
  toile2: { tessera: "#4d7c0f", chaud: "#6b8a2a", neon: "#1fd08a" },
  toile3: { tessera: "#fde047", chaud: "#f2c14e", neon: "#ffe14d" },
  toile4: { tessera: "#be185d", chaud: "#b8405e", neon: "#ff3d8b" },
  dore: { tessera: "#ca8a04", chaud: "#d4a03c", neon: "#ffc83d" },
  velours: { tessera: "#27272a", chaud: "#4a2630", neon: "#1a1640" },
  porte: { tessera: "#6b5038", chaud: "#7a4a2a", neon: "#33285a" },
  interrupteur: { tessera: "#d4d4d8", chaud: "#ebe3d0", neon: "#4a4f7a" },
});

/* ---------- Copies fidèles ---------- */

function avantMurFenetre({ jour = true, soleil = false, nuages = 0 } = {}) {
  const s = mk(20, 12), g = s.L();
  g.rect(0, 0, 20, 12, C.fenetreCadre); g.rect(1, 1, 18, 10, jour ? C.cielJour : C.cielNuit);
  const nuage = (x, y) => { g.rect(x, y + 1, 4, 1, C.nuage); g.rect(x + 1, y, 2, 1, C.nuage); };
  if (jour) { if (soleil) g.rect(13, 2, 3, 3, C.soleil); if (nuages >= 1) nuage(2, 3); if (nuages >= 2) nuage(13, 7); }
  else for (const [x, y] of [[4, 3], [6, 7], [14, 3], [16, 8]]) g.rect(x, y, 1, 1, C.etoile);
  g.rect(9, 1, 2, 10, C.fenetreCadre);
  return s;
}
/** Le cône de lumière est un dégradé SVG qui déborde de la grille : il n'est pas recopié ici. */
function avantMurPlafonnier(allume) {
  const s = mk(12, 8), g = s.L();
  g.rect(5, 0, 2, 2, C.fenetreCadre); g.rect(2, 2, 8, 2, C.fenetreCadre); g.rect(3, 4, 6, 1, allume ? C.plafonnier : C.cadreFond);
  return s;
}
function avantMurTableau(cases) {
  const s = mk(44, 27), g = s.L(), largeur = cases.length > 6 ? 15 : 36;
  const ton = { attente: C.tableauCase, passe: C.vert500, echoue: C.rouge500 };
  g.rect(0, 0, 44, 27, C.tableauCadre); g.rect(1, 1, 42, 25, C.tableau);
  cases.slice(0, 12).forEach((etat, i) => {
    const x = 2 + Math.floor(i / 6) * 21, y = 2 + (i % 6) * 4;
    g.rect(x, y, 3, 3, ton.attente); g.rect(x + 1, y + 1, 1, 1, C.tableau);
    const marque = etat === "passe" ? [[2, 0], [0, 1], [2, 1], [1, 2]] : etat === "echoue" ? [[0, 0], [2, 0], [1, 1], [0, 2], [2, 2]] : null;
    if (marque) { g.rect(x, y, 3, 3, C.tableau); for (const [dx, dy] of marque) g.rect(x + dx, y + dy, 1, 1, ton[etat]); }
    g.rect(x + 4, y + 1, largeur, 1, ton[etat]);
  });
  return s;
}
/** Les aiguilles tournent d'un angle libre dans Tessera : la copie les pose au pixel le plus proche. */
function avantMurHorloge(h = 10, m = 10) {
  const s = mk(8, 8), g = s.L();
  g.rect(0, 0, 8, 8, C.horlogeBord); g.rect(1, 1, 6, 6, C.horlogeCadran);
  const aiguille = (deg, L) => { const a = deg * Math.PI / 180; g.line(4, 4, Math.round(4 + L * Math.sin(a)), Math.round(4 - L * Math.cos(a)), C.horlogeAiguille); };
  aiguille((h % 12) * 30 + m * .5, 2); aiguille(m * 6, 3);
  return s;
}
function avantMurCadre(image) {
  const s = mk(10, 12), g = s.L(), T = C.toiles;
  g.rect(0, 0, 10, 12, C.cadreBois);
  if (image === 0) { g.rect(1, 1, 8, 10, T[0]); g.rect(1, 7, 8, 4, T[1]); g.rect(6, 2, 2, 2, T[2]); }
  else if (image === 1) { g.rect(1, 1, 8, 10, T[3]); g.rect(3, 3, 4, 4, T[2]); g.rect(1, 9, 8, 2, T[1]); }
  else if (image === 2) { g.rect(1, 1, 8, 10, T[2]); g.rect(1, 4, 8, 2, T[1]); g.rect(1, 8, 8, 3, T[0]); }
  else { g.rect(1, 1, 8, 10, T[1]); g.rect(1, 1, 4, 5, T[3]); g.rect(5, 6, 4, 5, T[0]); }
  return s;
}
function avantMurCadreDore(ph = PH.codeur) {
  const s = mk(16, 17), g = s.L();
  g.rect(0, 0, 16, 17, C.cadreDore); g.rect(1, 1, 14, 15, C.cadreFond);
  avantTete(g, ph, 5, 6);
  g.rect(4, 10, 8, 5, C.haut.codeur); g.rect(6, 10, 4, 1, C.ombre.codeur);
  g.rect(3, 12, 2, 3, C.ombre.codeur); g.rect(11, 12, 2, 3, C.ombre.codeur);
  return s;
}
function avantMurPorte() {
  const s = mk(12, 18), g = s.L();
  g.rect(0, 0, 12, 18, C.porteOmbre); g.rect(1, 1, 10, 17, C.porte);
  for (const [x, y, w, h] of [[2, 3, 3, 5], [7, 3, 3, 5], [2, 10, 3, 6], [7, 10, 3, 6]]) g.rect(x, y, w, h, C.porteOmbre);
  g.rect(9, 9, 1, 1, C.tasse);
  return s;
}
function avantMurInterrupteur(allume) {
  const s = mk(6, 9), g = s.L();
  g.rect(0, 0, 6, 9, C.interrupteur); g.rect(2, allume ? 2 : 4, 2, 3, C.interrupteurTouche);
  return s;
}
function avantMurEtagere() {
  const s = mk(16, 10), g = s.L();
  g.rect(1, 1, 2, 2, C.plante); g.rect(3, 0, 2, 3, C.planteO); g.rect(2, 3, 4, 3, C.pot);
  g.rect(8, 2, 2, 4, C.livres[0]); g.rect(10, 3, 3, 3, C.livres[1]);
  g.rect(0, 6, 16, 2, C.etagere); g.rect(1, 8, 2, 2, C.etagere); g.rect(13, 8, 2, 2, C.etagere);
  return s;
}

/* ---------- Grille ×2 ---------- */

/** Le ciel derrière la vitre, pixel par pixel : plus sombre en haut, plus clair à l'horizon. */
function murCiel(jour, x, y) {
  const dither = (x + y) % 2 === 0;
  if (jour) {
    if (y <= 3 || (y === 4 && dither)) return "ciel.s";
    if (y >= 16 || (y === 15 && dither)) return "ciel.hi";
    return "ciel.b";
  }
  if (y <= 5 || (y === 6 && dither)) return "ciel-nuit.s";
  if (y >= 17 || (y === 16 && dither)) return "ciel-nuit.hi";
  return "ciel-nuit.b";
}
/** Un nuage de 8 × 4, sa bosse en haut à gauche, son ventre dans l'ombre. */
function murNuage(g, x, y) {
  g.stamp(x, y, ["..hhh...", ".hhbbbh.", "hbbbbbbb", ".sssss.."], { h: "nuage.hi", b: "nuage.b", s: "nuage.s" });
}
/**
 * La fenêtre, 40 × 24. Le ciel suit l'heure de la vue (de 7 h à 19 h, clair) : c'est une
 * donnée, pas un état. `soleil` le jour ; la nuit, la même fenêtre porte la lune.
 */
function murFenetre({ jour = true, soleil = false, nuages = 0 } = {}) {
  const s = mk(40, 24), g = s.L(), F = R("fenetre");
  for (let y = 2; y <= 20; y++) for (let x = 2; x <= 37; x++) g.px(x, y, murCiel(jour, x, y));
  const v = s.L();
  if (jour) {
    if (soleil) { v.disc(29, 7, 3, "soleil", { shade: false }); v.rect(27, 6, 2, 1, "soleil.hi"); v.px(28, 5, "soleil.hi"); v.rect(30, 9, 2, 1, "soleil.s"); v.px(31, 8, "soleil.s"); }
    if (nuages >= 1) murNuage(v, 4, 6);
    if (nuages >= 2) murNuage(v, 26, 14);
  } else {
    if (soleil) v.stamp(27, 4, ["..bbb", ".hb..", "hb...", "hb...", "hb...", ".hb..", "..bbb"], { h: "etoile.hi", b: "etoile.b" });
    for (const [x, y] of [[12, 14], [32, 16], [16, 5]]) v.px(x, y, "etoile.b");
    // Deux étoiles en croix, qui scintillent : décor du ciel, aucun état.
    [[8, 6], [24, 10]].forEach(([x, y], i) => {
      const e = s.L("anim-scintille", `animation-delay:-${i * 1.3}s`);
      e.px(x, y, "etoile.hi"); e.px(x - 1, y, "etoile.s"); e.px(x + 1, y, "etoile.s"); e.px(x, y - 1, "etoile.s"); e.px(x, y + 1, "etoile.s");
    });
  }
  // Reflets sur la vitre, en haut à gauche de chaque carreau.
  const r = s.L(), reflet = jour ? "ciel.hi" : "ciel-nuit.hi";
  r.line(4, 11, 10, 5, reflet); r.line(5, 13, 8, 10, reflet); r.line(22, 9, 25, 6, reflet);
  // Cadre, meneau, appui.
  const c = s.L();
  c.rect(0, 0, 40, 2, F.b); c.rect(0, 0, 2, 22, F.b); c.rect(38, 0, 2, 22, F.b); c.rect(0, 20, 40, 1, F.b);
  c.rect(0, 0, 40, 1, F.hi); c.rect(0, 0, 1, 21, F.hi); c.rect(39, 1, 1, 20, F.s); c.rect(2, 1, 36, 1, F.b);
  c.rect(1, 1, 1, 20, F.b); c.rect(38, 2, 1, 18, F.d);
  c.rect(19, 2, 2, 18, F.b); c.rect(19, 2, 1, 18, F.hi); c.rect(20, 2, 1, 18, F.s);
  c.rect(0, 21, 40, 1, F.hi); c.rect(0, 22, 40, 1, F.b); c.rect(0, 23, 40, 1, F.s); c.rect(39, 21, 1, 3, F.d);
  return s;
}

/**
 * Le plafonnier, 24 × 16 : patère, tige, abat-jour émaillé, diffuseur. Allumé, le
 * diffuseur s'éclaire et laisse filer une lèvre de lumière ; le cône reste le dégradé
 * de Tessera, qui déborde de la grille.
 */
function murPlafonnier(allume = true) {
  const s = mk(24, 16), g = s.L(), M = P.metal, Lp = R("lampe");
  g.rect(8, 0, 8, 2, M.b); g.rect(8, 0, 8, 1, M.hi); g.rect(15, 1, 1, 1, M.s);
  g.rect(11, 2, 2, 3, M.s); g.px(11, 2, M.b);
  // Abat-jour : un dôme qui s'évase.
  g.rect(8, 5, 8, 1, M.b); g.rect(6, 6, 12, 1, M.b); g.rect(4, 7, 16, 2, M.b); g.rect(3, 9, 18, 1, M.s);
  g.rect(9, 5, 3, 1, M.hi); g.rect(7, 6, 3, 1, M.hi); g.rect(5, 7, 3, 1, M.hi);
  g.rect(14, 6, 4, 1, M.s); g.rect(16, 7, 4, 2, M.s); g.rect(19, 7, 1, 2, M.d); g.rect(17, 9, 4, 1, M.d);
  const d = s.L();
  if (allume) {
    d.rect(6, 10, 12, 2, Lp.b); d.rect(7, 10, 5, 1, Lp.hi);
    d.rect(9, 12, 6, 1, Lp.hi);
  } else {
    d.rect(6, 10, 12, 2, P.frame.b); d.rect(7, 10, 3, 1, P.frame.hi); d.rect(14, 11, 4, 1, P.frame.s);
  }
  return s;
}

/** Les mots d'une ligne manuscrite : longueurs fixes par critère, comme une écriture. */
const MUR_MOTS = [[9, 5, 13, 7, 11, 6, 8], [6, 11, 4, 9, 14, 7], [12, 4, 8, 10, 6, 13], [7, 9, 5, 12, 8, 11], [10, 6, 9, 4, 13, 7], [5, 12, 7, 8, 10, 9]];
const MUR_COCHE = [".....x", "....xx", "x..xx.", "xxxx..", ".xx..."];
const MUR_CROIX = ["xx..xx", ".xxxx.", "..xx..", "..xx..", ".xxxx.", "xx..xx"];
/** L'état d'une case → la famille d'état qui la dessine (ADR-026). */
const MUR_ETAT_CASE = { attente: "attente", passe: "fait", echoue: "blocage" };

/**
 * Le tableau blanc, 88 × 54 : cadre alu, reflet, rebord à feutres. Une case et une ligne
 * manuscrite par critère, tons d'état : gris en attente, vert si le critère passe, rouge sinon.
 */
function murTableau(cases = []) {
  const s = mk(88, 54), g = s.L(), M = P.metal, T = R("tableau");
  g.rect(0, 0, 88, 54, M.b); g.rect(0, 0, 88, 1, M.hi); g.rect(0, 0, 1, 54, M.hi); g.rect(87, 1, 1, 53, M.s); g.rect(1, 53, 87, 1, M.s);
  g.rect(2, 2, 84, 50, T.b); g.rect(85, 2, 1, 50, T.s); g.rect(2, 51, 84, 1, T.s); g.rect(2, 2, 83, 1, T.hi);
  // Un reflet en biais, en haut à droite.
  for (let i = 0; i < 6; i++) { g.px(80 - i, 4 + i, T.hi); g.px(81 - i, 4 + i, T.hi); g.px(84 - i, 4 + i, T.hi); }
  const colonnes = cases.length > 6 ? 2 : 1, largeur = colonnes === 2 ? 30 : 72;
  const m = s.L();
  cases.slice(0, 12).forEach((etat, i) => {
    const x = 4 + Math.floor(i / 6) * 42, y = 4 + (i % 6) * 7, L = E(MUR_ETAT_CASE[etat]);
    if (etat === "attente") { m.rect(x, y, 6, 6, L.s); m.rect(x + 1, y + 1, 4, 4, T.b); }
    else m.stamp(x, y, etat === "passe" ? MUR_COCHE : MUR_CROIX, { x: L.d });
    // La ligne : des mots au feutre, de la même longueur totale que la ligne d'aujourd'hui.
    let wx = x + 8;
    const fin = x + 8 + largeur;
    for (const n of MUR_MOTS[i % 6]) {
      if (wx >= fin) break;
      const w = Math.min(n, fin - wx);
      m.rect(wx, y + 2, w, 2, L.s); if (w > 3) m.px(wx, y + 1, L.s);
      wx += w + 2;
    }
  });
  // Rebord, un feutre noir, une brosse.
  const r = s.L();
  r.rect(4, 50, 80, 1, M.hi); r.rect(4, 51, 80, 2, M.b); r.rect(4, 52, 80, 1, M.s);
  r.rect(58, 48, 8, 2, P.ink); r.rect(58, 48, 2, 2, "encre.hi"); r.px(66, 49, P.ink);
  r.rect(70, 47, 9, 2, P.wood.b); r.rect(70, 47, 9, 1, P.wood.hi); r.rect(70, 49, 9, 1, P.clavier.s);
  return s;
}

/**
 * L'horloge murale, 16 × 16 : un cadran rond dans sa lunette, quatre repères, deux
 * aiguilles. L'heure est une donnée : les aiguilles suivent l'horloge de la vue.
 */
function murHorloge(h = 10, m = 10) {
  const s = mk(16, 16), g = s.L();
  g.disc(7.5, 7.5, 7.6, "metal");
  const f = s.L();
  f.disc(7.5, 7.5, 5.7, "cadran", { shade: false });
  const dedans = (x, y) => f.get(x, y) !== null;
  for (let y = 0; y < 16; y++) for (let x = 0; x < 16; x++) {
    if (!dedans(x, y)) continue;
    if (!dedans(x - 1, y - 1)) f.px(x, y, "cadran.s");
    else if (!dedans(x + 1, y + 1)) f.px(x, y, "cadran.hi");
  }
  f.rect(7, 3, 2, 1, "cadran.d"); f.rect(7, 12, 2, 1, "cadran.d"); f.rect(3, 7, 1, 2, "cadran.d"); f.rect(12, 7, 1, 2, "cadran.d");
  const a = s.L();
  const aiguille = (deg, L) => {
    const t = deg * Math.PI / 180, dx = Math.sin(t), dy = -Math.cos(t);
    a.line(Math.floor(7.5 + 1.2 * dx + .5 * Math.sign(dx)), Math.floor(7.5 + 1.2 * dy + .5 * Math.sign(dy)), Math.floor(8 + L * dx), Math.floor(8 + L * dy), P.ink);
  };
  aiguille((h % 12) * 30 + m * .5, 3); aiguille(m * 6, 5);
  a.rect(7, 7, 2, 2, P.ink); a.px(7, 7, P.metal.hi);
  return s;
}

/** Les quatre tableaux du cadre, 16 × 20 : paysage, soleil, champ, composition. */
function murToile(g, image, x0, y0) {
  const t = n => R("toile" + n), r = (x, y, w, h, c) => g.rect(x0 + x, y0 + y, w, h, c), p = (x, y, c) => g.px(x0 + x, y0 + y, c);
  if (image === 0) {
    r(0, 0, 16, 12, t(1).b); r(0, 0, 16, 3, t(1).s); r(0, 9, 16, 3, t(1).hi);
    g.disc(x0 + 12, y0 + 5, 2, "toile3");
    r(0, 12, 16, 8, t(2).b); r(0, 11, 7, 1, t(2).b); r(2, 10, 3, 1, t(2).b); r(11, 11, 5, 1, t(2).s);
    r(9, 13, 7, 7, t(2).s); r(1, 11, 3, 1, t(2).hi); r(0, 18, 16, 2, t(2).d); p(4, 15, t(2).hi); p(7, 16, t(2).hi);
  } else if (image === 1) {
    r(0, 0, 16, 20, t(4).b); r(0, 0, 16, 3, t(4).s); r(0, 12, 16, 4, t(4).hi);
    g.disc(x0 + 7.5, y0 + 7.5, 4, "toile3"); p(5, 5, t(3).hi);
    r(0, 16, 16, 4, t(2).b); r(0, 16, 16, 1, t(2).hi); r(10, 17, 6, 3, t(2).s);
  } else if (image === 2) {
    r(0, 0, 16, 20, t(3).b); r(0, 0, 16, 2, t(3).hi); r(0, 5, 16, 1, t(3).s);
    r(0, 6, 16, 4, t(2).b); r(0, 6, 16, 1, t(2).hi); r(0, 9, 16, 1, t(2).s);
    for (const [x, y] of [[2, 11], [6, 12], [10, 11], [13, 12], [4, 13]]) { p(x, y, t(3).s); p(x, y - 1, t(3).hi); }
    r(0, 14, 16, 6, t(1).b); r(0, 14, 16, 1, t(1).hi); r(2, 16, 4, 1, t(1).hi); r(9, 18, 5, 1, t(1).hi); r(0, 19, 16, 1, t(1).s);
  } else {
    r(0, 0, 16, 20, t(2).b);
    r(0, 0, 8, 10, t(4).b); r(0, 0, 8, 1, t(4).hi); r(7, 1, 1, 9, t(4).s);
    r(8, 10, 8, 10, t(1).b); r(8, 10, 8, 1, t(1).hi); r(15, 11, 1, 9, t(1).s);
    r(10, 3, 3, 3, t(3).b); p(10, 3, t(3).hi);
    r(2, 13, 3, 3, t(2).s); r(8, 0, 8, 1, t(2).hi); r(0, 19, 8, 1, t(2).s);
  }
}
/** Le cadre, 20 × 24 : baguette en bois en relief, la toile en retrait. Seule l'image varie. */
function murCadre(image = 0) {
  const s = mk(20, 24), g = s.L(), W = P.wood;
  g.rect(0, 0, 20, 24, W.b); g.rect(0, 0, 20, 1, W.hi); g.rect(0, 0, 1, 24, W.hi); g.rect(19, 1, 1, 23, W.s); g.rect(1, 23, 19, 1, W.s);
  g.rect(1, 1, 18, 1, W.d); g.rect(1, 1, 1, 22, W.d); g.rect(18, 2, 1, 21, W.hi); g.rect(2, 22, 17, 1, W.hi);
  murToile(g, image, 2, 2);
  return s;
}

/** Le cadre de l'employé de la semaine, 32 × 34 : baguette dorée perlée, fond de velours, buste du codeur. */
function murCadreDore(ph = PH.codeur) {
  const s = mk(32, 34), g = s.L(), D = R("dore"), V = R("velours"), T = P.top.codeur, K = P.skin[ph.peau - 1];
  g.rect(3, 3, 26, 28, V.s); g.disc(15.5, 15, 11, "velours", { shade: false }); g.disc(14, 13, 6, "velours", { shade: false });
  g.rect(3, 3, 26, 1, V.d); g.rect(3, 3, 1, 28, V.d);
  tete(g, 10, 12, ph);
  g.rect(14, 21, 4, 1, K.s);
  g.rect(9, 22, 14, 9, T.b); g.rect(8, 23, 16, 8, T.b); g.rect(20, 23, 4, 8, T.s); g.rect(9, 23, 4, 1, T.hi); g.px(9, 24, T.hi);
  torseDetails(g, "codeur", 9, 22);
  const c = s.L();
  c.rect(0, 0, 32, 3, D.b); c.rect(0, 31, 32, 3, D.b); c.rect(0, 0, 3, 34, D.b); c.rect(29, 0, 3, 34, D.b);
  c.rect(0, 0, 32, 1, D.hi); c.rect(0, 0, 1, 34, D.hi); c.rect(31, 1, 1, 33, D.s); c.rect(1, 33, 31, 1, D.s);
  for (let x = 3; x < 29; x += 2) { c.px(x, 1, D.hi); c.px(x, 32, D.s); }
  for (let y = 3; y < 31; y += 2) { c.px(1, y, D.hi); c.px(30, y, D.s); }
  c.rect(2, 2, 28, 1, D.d); c.rect(2, 2, 1, 30, D.d); c.rect(29, 3, 1, 28, D.hi); c.rect(3, 31, 27, 1, D.hi);
  for (const [x, y] of [[0, 0], [29, 0], [0, 31], [29, 31]]) { c.rect(x + 1, y + 1, 2, 2, D.hi); c.px(x + 2, y + 2, D.s); }
  // La plaque gravée, au bas du cadre.
  c.rect(11, 29, 10, 4, D.s); c.rect(12, 29, 8, 3, D.hi); for (let x = 13; x < 19; x += 2) c.px(x, 30, D.s);
  return s;
}

/** La porte, 24 × 36 : chambranle, quatre panneaux à plate-bande, poignée en laiton, plaque de propreté. */
function murPorte() {
  const s = mk(24, 36), g = s.L(), Pt = R("porte"), D = R("dore"), M = P.metal;
  g.rect(0, 0, 24, 36, Pt.s); g.rect(0, 0, 24, 1, Pt.b); g.rect(0, 0, 1, 36, Pt.b); g.rect(23, 1, 1, 35, Pt.d);
  g.rect(2, 2, 20, 34, Pt.b); g.rect(2, 2, 20, 1, Pt.d); g.rect(2, 2, 1, 34, Pt.d); g.rect(21, 3, 1, 33, Pt.s);
  g.rect(3, 3, 18, 1, Pt.hi);
  for (const [x, y, w, h] of [[4, 6, 6, 10], [14, 6, 6, 10], [4, 20, 6, 12], [14, 20, 6, 12]]) {
    g.rect(x, y, w, h, Pt.s); g.rect(x, y, w, 1, Pt.d); g.rect(x, y, 1, h, Pt.d);
    g.rect(x + 1, y + h - 1, w - 1, 1, Pt.hi); g.rect(x + w - 1, y + 1, 1, h - 1, Pt.hi);
    g.rect(x + 2, y + 2, w - 4, h - 4, Pt.b); g.px(x + 2, y + 2, Pt.hi);
  }
  for (const y of [9, 13, 24, 28]) { g.px(6, y, Pt.s); g.px(16, y + 1, Pt.s); }
  g.rect(18, 16, 2, 4, D.s); g.rect(17, 17, 3, 2, D.b); g.px(17, 17, D.hi); g.px(19, 18, D.d);
  g.rect(3, 33, 18, 3, M.b); g.rect(3, 33, 18, 1, M.hi); g.rect(3, 35, 18, 1, M.s);
  return s;
}

/** L'interrupteur, 12 × 18 : plaque bombée, deux vis, bascule enfoncée du côté éteint. */
function murInterrupteur(allume = true) {
  const s = mk(12, 18), g = s.L(), I = R("interrupteur"), M = P.metal;
  g.rect(0, 0, 12, 18, I.b); g.rect(0, 0, 12, 1, I.hi); g.rect(0, 0, 1, 18, I.hi); g.rect(11, 1, 1, 17, I.s); g.rect(1, 17, 11, 1, I.s);
  g.clr(0, 0); g.clr(11, 0); g.clr(0, 17); g.clr(11, 17);
  g.rect(5, 1, 2, 1, M.s); g.px(5, 1, M.b); g.rect(5, 16, 2, 1, M.s); g.px(5, 16, M.b);
  g.rect(3, 3, 6, 12, I.d);
  if (allume) { g.rect(4, 4, 4, 5, I.b); g.rect(4, 4, 4, 1, I.hi); g.rect(4, 4, 1, 5, I.hi); g.rect(4, 9, 4, 5, I.s); g.rect(7, 9, 1, 5, I.d); }
  else { g.rect(4, 4, 4, 5, I.s); g.rect(7, 4, 1, 5, I.d); g.rect(4, 9, 4, 5, I.b); g.rect(4, 9, 4, 1, I.hi); g.rect(4, 9, 1, 5, I.hi); }
  return s;
}

/** L'étagère, 32 × 20 : planche sur deux équerres, une plante en pot, deux livres debout, un couché. */
function murEtagere() {
  const s = mk(32, 20), g = s.L(), W = P.wood;
  g.rect(6, 5, 2, 2, P.plant.d);
  feuillage(g, "plante", [[4.5, 4, 2.2], [9.5, 3.5, 2.2], [7, 2, 2], [7, 5, 2]]);
  pot(g, P.pot, 3, 6, 8, 3);
  const livre = (x, y, w, h, B) => { g.rect(x, y, w, h, B.b); g.rect(x, y, 1, h, B.hi); g.rect(x + w - 1, y, 1, h, B.s); g.rect(x, y + 2, w, 1, B.d); g.rect(x, y + h - 3, w, 1, B.d); };
  livre(16, 4, 4, 8, P.books[0]); livre(20, 6, 6, 6, P.books[1]);
  g.rect(26, 9, 5, 3, P.books[2].b); g.rect(26, 9, 5, 1, P.books[2].hi); g.rect(26, 10, 4, 1, P.cup.b); g.rect(30, 10, 1, 2, P.books[2].s);
  g.rect(0, 12, 32, 4, W.b); g.rect(0, 12, 32, 1, W.hi); g.rect(0, 15, 32, 1, W.s); g.rect(31, 13, 1, 3, W.s);
  for (const [x, y] of [[5, 13], [6, 13], [18, 14], [19, 14], [27, 13]]) g.px(x, y, W.s);
  for (const x0 of [2, 26]) for (let j = 0; j < 4; j++) { g.rect(x0, 16 + j, 4 - j, 1, W.s); g.px(x0, 16 + j, W.b); }
  return s;
}

/* ---------- Registre ---------- */

enregistrer({ id: "mur-fenetre-jour", nom: "Fenêtre, jour", fichier: "SkyWindow", salle: "ambiance", grille: "20 × 12 → 40 × 24", dw: 60, dh: 36,
  avant: () => avantMurFenetre({ jour: true, soleil: true, nuages: 2 }), apres: () => murFenetre({ jour: true, soleil: true, nuages: 2 }),
  variante: { label: "Sans soleil, un nuage", f: () => murFenetre({ jour: true, nuages: 1 }) },
  note: "Un ciel en dégradé, plus clair à l'horizon, un soleil rond, des nuages en relief, des reflets sur la vitre et un appui. Le ciel reste une donnée : clair de 7 h à 19 h." });
enregistrer({ id: "mur-fenetre-nuit", nom: "Fenêtre, nuit", fichier: "SkyWindow", salle: "ambiance", grille: "20 × 12 → 40 × 24", dw: 60, dh: 36,
  avant: () => avantMurFenetre({ jour: false }), apres: () => murFenetre({ jour: false }),
  variante: { label: "La fenêtre au soleil porte la lune", f: () => murFenetre({ jour: false, soleil: true }) },
  note: "Un ciel de nuit en dégradé, cinq étoiles dont deux en croix qui scintillent doucement. La fenêtre qui porte le soleil le jour pourrait porter un croissant de lune la nuit." });
enregistrer({ id: "mur-plafonnier-allume", nom: "Plafonnier allumé", fichier: "CeilingLamp", salle: "ambiance", grille: "12 × 8 → 24 × 16", dw: 36, dh: 24,
  avant: () => avantMurPlafonnier(true), apres: () => murPlafonnier(true),
  note: "Un abat-jour en dôme émaillé au lieu d'une barre, un diffuseur qui s'éclaire. Le cône de lumière reste le dégradé de Tessera, hors de la grille." });
enregistrer({ id: "mur-plafonnier-eteint", nom: "Plafonnier éteint", fichier: "CeilingLamp", salle: "ambiance", grille: "12 × 8 → 24 × 16", dw: 36, dh: 24,
  avant: () => avantMurPlafonnier(false), apres: () => murPlafonnier(false),
  note: "Éteint, le diffuseur redevient du verre sombre avec un reflet : on voit qu'il y a une lampe, pas qu'elle brille." });
enregistrer({ id: "mur-tableau", nom: "Tableau blanc, quatre critères", fichier: "TableauBlanc", salle: "run", grille: "44 × 27 → 88 × 54", dw: 88, dh: 54,
  avant: () => avantMurTableau(["passe", "passe", "echoue", "attente"]), apres: () => murTableau(["passe", "passe", "echoue", "attente"]),
  note: "Des coches et des croix tracées au feutre, des lignes écrites en mots, un reflet, un rebord avec un feutre et une brosse. Gris, vert et rouge restent les tons d'état." });
enregistrer({ id: "mur-tableau-plein", nom: "Tableau blanc, neuf critères", fichier: "TableauBlanc", salle: "run", grille: "44 × 27 → 88 × 54", dw: 88, dh: 54,
  avant: () => avantMurTableau(["passe", "passe", "passe", "echoue", "passe", "attente", "attente", "attente", "attente"]),
  apres: () => murTableau(["passe", "passe", "passe", "echoue", "passe", "attente", "attente", "attente", "attente"]),
  note: "Au-delà de six critères, la seconde colonne garde les mêmes lignes courtes qu'aujourd'hui." });
enregistrer({ id: "mur-tableau-vierge", nom: "Tableau blanc vierge", fichier: "TableauBlanc", salle: "run", grille: "44 × 27 → 88 × 54", dw: 88, dh: 54,
  avant: () => avantMurTableau([]), apres: () => murTableau([]),
  note: "Sans critère, le tableau reste blanc : seuls le reflet et le rebord le distinguent d'un mur." });
enregistrer({ id: "mur-horloge", nom: "Horloge murale", fichier: "Horloge", salle: "run", grille: "8 × 8 → 16 × 16", dw: 16, dh: 16,
  avant: () => avantMurHorloge(10, 10), apres: () => murHorloge(10, 10),
  variante: { label: "16 h 40", f: () => murHorloge(16, 40) },
  note: "Un cadran rond dans une lunette en métal, quatre repères, un axe. Les aiguilles suivent toujours l'heure de la vue, sans trotteuse." });
const MUR_IMAGES = ["paysage", "soleil", "champ", "composition"];
MUR_IMAGES.forEach((nom, image) => enregistrer({ id: `mur-cadre-${nom}`, nom: `Cadre, ${nom}`, fichier: "Cadre", salle: "run", grille: "10 × 12 → 20 × 24", dw: 20, dh: 24,
  avant: () => avantMurCadre(image), apres: () => murCadre(image),
  note: ["Une baguette en relief ; le paysage gagne des collines, un soleil rond et un ciel en dégradé.",
    "Le carré jaune devient un soleil rond sur un fond qui s'éclaire vers l'horizon.",
    "Un champ, une haie et de l'eau avec des reflets, toujours en trois bandes.",
    "La composition garde ses trois aplats, avec un petit carré jaune et des bords en relief."][image] }));
enregistrer({ id: "mur-cadre-dore", nom: "Cadre de l'employé de la semaine", fichier: "GoldFrame", salle: "run", grille: "16 × 17 → 32 × 34", dw: 32, dh: 34,
  avant: () => avantMurCadreDore(), apres: () => murCadreDore(),
  variante: { label: "Autre physique", f: () => murCadreDore(PH.reviewer) },
  note: "Une baguette dorée perlée avec ses coins, un fond de velours éclairé derrière la tête, le buste du codeur du projet et une plaque gravée." });
enregistrer({ id: "mur-porte", nom: "Porte", fichier: "Porte", salle: "run", grille: "12 × 18 → 24 × 36", dw: 36, dh: 54,
  avant: () => avantMurPorte(), apres: () => murPorte(),
  note: "Des panneaux à plate-bande en relief, un chambranle, une poignée en laiton et une plaque de propreté en bas. Toujours sans voyant." });
enregistrer({ id: "mur-interrupteur-allume", nom: "Interrupteur, allumé", fichier: "Interrupteur", salle: "run", grille: "6 × 9 → 12 × 18", dw: 5.5, dh: 8.25,
  avant: () => avantMurInterrupteur(true), apres: () => murInterrupteur(true),
  note: "Une plaque aux coins arrondis avec deux vis ; la bascule est enfoncée en bas quand la lumière est allumée." });
enregistrer({ id: "mur-interrupteur-eteint", nom: "Interrupteur, éteint", fichier: "Interrupteur", salle: "run", grille: "6 × 9 → 12 × 18", dw: 5.5, dh: 8.25,
  avant: () => avantMurInterrupteur(false), apres: () => murInterrupteur(false),
  note: "Éteint, la bascule s'enfonce en haut : le relief dit la position, sans couleur ajoutée." });
enregistrer({ id: "mur-etagere", nom: "Étagère murale", fichier: "Etagere", salle: "run", grille: "16 × 10 → 32 × 20", dw: 32, dh: 20,
  avant: () => avantMurEtagere(), apres: () => murEtagere(),
  note: "Une planche veinée sur deux équerres, une plante en touffes dans son pot, deux reliures et un livre couché." });
