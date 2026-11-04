"use strict";
/*
 * Salle des serveurs, suite : petite baie de la pièce de run, chemin de câbles, bouche VMC,
 * extincteur, porte coupe-feu, dalles du faux plancher ; puis les scènes d'écran d'un poste.
 * Grille ×2, jetons seulement. Seuls les voyants et les traits d'écran portent un état (ADR-058).
 */

Object.assign(FAMILLES, {
  dalle: { tessera: "#2a2e33", chaud: "#34302c", neon: "#14162e" },
  "salle-plinthe": { tessera: "#16191c", chaud: "#1f1a17", neon: "#07081a" },
  extincteur: { tessera: "#dc2626", chaud: "#d2402a", neon: "#ff2e63" },
  badge: { tessera: "#d4d4d8", chaud: "#e6dcc8", neon: "#b8bdf5" },
  "ecran-fond": { tessera: "#18181b", chaud: "#1c1719", neon: "#05061a" },
  "ecran-page": { tessera: "#d4d4d8", chaud: "#ece4d2", neon: "#cfd3ff" },
});

Object.assign(C, {
  z300: "#d4d4d8", dalle: "#2a2e33", dalleJoint: "#22262a", dalleTrou: "#16191c", sallePlinthe: "#16191c",
  extincteur: "#dc2626", extincteurO: "#991b1b", badge: "#d4d4d8",
  blue400: "#60a5fa", red400: "#f87171", green400: "#4ade80", amber400: "#fbbf24",
});

/* ---------- Copies fidèles ---------- */

/** Baie.tsx : un étage par service. `etats` dans le vocabulaire de Tessera. */
const SRV_VOYANT_AVANT = { "en-cours": C.blue400, echoue: C.red400, arrete: C.z500, "jamais-lance": C.z600 };
function avantPetiteBaie(etats = ["en-cours", "echoue", "arrete"]) {
  const h = etats.length * 4 + 2, s = mk(12, h), g = s.L();
  g.rect(0, 0, 12, h, C.z700);
  etats.forEach((e, i) => { g.rect(1, 1 + i * 4, 10, 3, C.z800); g.rect(2, 2 + i * 4, 1, 1, SRV_VOYANT_AVANT[e]); });
  return s;
}
/** CheminDeCables.tsx : un tronçon de 40 sur les 200 de la grille, qui se répète à l'identique. */
function avantChemin() {
  const s = mk(40, 8), g = s.L();
  g.rect(0, 0, 40, 1, C.metal); g.rect(0, 1, 40, 2, C.metalO);
  for (let x = 0; x < 40; x += 2) g.rect(x, 1, 1, 1, C.metal);
  g.rect(0, 3, 40, 1, C.sallePlinthe);
  return s;
}
function avantVmc() {
  const s = mk(14, 14), g = s.L();
  g.rect(0, 0, 14, 14, C.metalO); g.rect(1, 1, 12, 12, C.metal); g.rect(2, 2, 10, 10, C.dalleTrou);
  const h = s.L(); h.rect(6, 3, 2, 3, C.metalC); h.rect(6, 8, 2, 3, C.metalC); h.rect(3, 6, 3, 2, C.metalC); h.rect(8, 6, 3, 2, C.metalC);
  const m = s.L(); m.rect(6, 6, 2, 2, C.metalO);
  // Les lames de la grille font un demi-pixel à 60 % : arrondies ici à une ligne pleine.
  const l = s.L("", "opacity:.6"); for (const y of [3, 5, 7, 9, 11]) l.rect(2, y, 10, 1, C.metalO);
  return s;
}
function avantExtincteur() {
  const s = mk(6, 14), g = s.L();
  g.rect(1, 0, 3, 1, C.metalC); g.rect(4, 1, 2, 1, C.metalC); g.rect(2, 1, 2, 2, C.metal);
  g.rect(1, 3, 4, 11, C.extincteur); g.rect(4, 3, 1, 11, C.extincteurO); g.rect(1, 7, 3, 3, C.badge);
  return s;
}
function avantPorte() {
  const s = mk(14, 18), g = s.L();
  g.rect(0, 0, 11, 18, C.metalO); g.rect(1, 1, 9, 17, C.metal); g.rect(2, 3, 7, 3, C.metalO); g.rect(2, 12, 7, 1, C.metalO);
  g.rect(8, 9, 1, 2, C.metalC); g.rect(11, 7, 3, 5, C.metalO); g.rect(12, 8, 1, 2, C.badge);
  return s;
}
function avantDalle(perforee) {
  const s = mk(12, 12), g = s.L();
  g.rect(0, 0, 12, 12, C.dalleJoint); g.rect(1, 1, 10, 10, C.dalle);
  if (perforee) for (const y of [3, 5, 7, 9]) for (const x of [3, 5, 7, 9]) g.rect(x, y, 1, 1, C.dalleTrou);
  return s;
}

/** EcranScenes.tsx, immobile (`anime` faux), sur le fond éteint de l'écran. `ton` : actif, question… */
const SRV_TON_ECRAN_AVANT = { actif: C.blue400, attente: C.z500, question: C.amber400, blocage: C.red400 };
function avantEcran(scene, ton = "actif") {
  const s = mk(6, 4), g = s.L(), T = SRV_TON_ECRAN_AVANT[ton];
  g.rect(0, 0, 6, 4, C.z900);
  const d = s.L();
  if (scene === "code") for (const k of [0, 4]) { d.rect(0, k, 4, 1, T); d.rect(1, k + 2, 3, 1, T); }
  if (scene === "lecture") { d.rect(1, 0, 4, 4, C.z300); d.rect(2, 1, 2, 1, C.z600); d.rect(2, 2, 2, 1, C.z600); }
  if (scene === "tests") { d.rect(0, 1, 6, 2, C.z700); d.rect(0, 1, 3, 2, T); }
  if (scene === "audit") { d.rect(0, 0, 6, 1, C.z700); d.rect(0, 2, 6, 1, C.z700); d.rect(0, 1, 6, 1, T); }
  if (scene === "diff") { d.rect(0, 0, 4, 1, C.green400); d.rect(0, 1, 3, 1, C.red400); d.rect(0, 2, 5, 1, C.green400); d.rect(0, 3, 2, 1, C.red400); }
  if (scene === "criteres") { d.rect(0, 0, 1, 1, C.z300); d.rect(2, 0, 3, 1, T); d.rect(0, 2, 1, 1, C.z300); d.rect(2, 2, 4, 1, T); }
  if (scene === "ok") [[0, 2], [1, 3], [2, 2], [3, 1], [4, 0]].forEach(([x, y]) => d.rect(x, y, 1, 1, C.green400));
  if (scene === "ko") [[1, 0], [4, 0], [2, 1], [3, 1], [2, 2], [3, 2], [1, 3], [4, 3]].forEach(([x, y]) => d.rect(x, y, 1, 1, C.red400));
  return s;
}

/* ---------- Grille ×2 ---------- */

/** L'état d'un service Tessera → l'état de l'atelier. « jamais-lancé » n'a pas de teinte à lui. */
const SRV_ETAT = { "en-cours": "actif", echoue: "blocage", arrete: "attente", "jamais-lance": "attente" };

/** La petite baie, 24 × (8 par étage + 4) : un serveur 2U par service, voyant à gauche, baies de disques. */
function srvPetiteBaie(etats = ["en-cours", "echoue", "arrete"]) {
  const h = etats.length * 8 + 4, s = mk(24, h), g = s.L(), M = P.metal;
  g.rect(0, 0, 24, h, M.d); g.rect(1, 1, 22, h - 2, M.s); g.rect(1, 1, 22, 1, M.b); g.rect(1, 1, 1, h - 2, M.b);
  const v = s.L();
  etats.forEach((e, i) => {
    const y = 2 + i * 8, L = E(SRV_ETAT[e]);
    g.rect(2, y, 20, 6, M.d); g.rect(3, y, 19, 5, M.b); g.rect(3, y, 19, 1, M.hi); g.rect(3, y, 1, 5, M.hi); g.rect(21, y + 1, 1, 4, M.s);
    // Le voyant, dans son logement.
    g.rect(4, y + 1, 4, 4, P.frame.d);
    v.rect(5, y + 2, 2, 2, L.b); v.px(5, y + 2, L.hi); v.px(6, y + 3, L.s);
    // Grille d'aération puis trois tiroirs de disques.
    for (let x = 9; x < 12; x += 1) for (let j = 1; j < 4; j += 2) g.px(x, y + j, M.d);
    for (const x of [13, 16, 19]) { g.rect(x, y + 1, 2, 3, M.s); g.px(x, y + 1, M.d); g.px(x + 1, y + 3, M.hi); }
  });
  g.rect(2, h - 2, 20, 1, M.d);
  return s;
}

/** Le chemin de câbles, tronçon 80 × 16 : caillebotis à fils, câbles vus à travers, une boucle qui pend. */
function srvChemin() {
  const s = mk(80, 16), g = s.L(), M = P.metal, K = P.frame, Pl = R("salle-plinthe");
  g.rect(0, 6, 80, 2, Pl.b); g.rect(0, 7, 80, 1, Pl.d);
  g.rect(0, 0, 80, 1, M.hi); g.rect(0, 1, 80, 1, M.b);
  g.rect(0, 2, 80, 4, M.d);
  // Les câbles couchés dans le chemin, entre les fils.
  g.rect(0, 2, 80, 1, K.b); g.rect(0, 3, 80, 1, K.s);
  for (let x = 3; x < 80; x += 11) g.px(x, 2, K.hi);
  for (let x = 0; x < 80; x += 4) { g.rect(x, 2, 1, 4, M.b); g.px(x, 2, M.hi); g.px(x + 1, 5, M.s); }
  g.rect(0, 4, 80, 1, M.s); g.rect(0, 5, 80, 1, M.s);
  for (let x = 0; x < 80; x += 4) g.px(x, 5, M.b);
  // Une boucle de câble qui s'échappe et pend sous le chemin.
  const c = s.L();
  [[50, 6], [51, 7], [52, 8], [53, 8], [54, 9], [55, 9], [56, 9], [57, 9], [58, 8], [59, 8], [60, 7], [61, 6]].forEach(([x, y]) => { c.px(x, y, K.b); c.px(x, y + 1, K.d); });
  c.px(54, 9, K.hi); c.px(55, 9, K.hi);
  return s;
}

/** Disque plein d'un seul jeton (le `disc` du moteur ombre, ici on veut une couleur unie). */
function srvRond(g, cx, cy, r, tok) {
  for (let y = Math.floor(cy - r); y <= cy + r; y++) for (let x = Math.floor(cx - r); x <= cx + r; x++) {
    const dx = x + .5 - cx, dy = y + .5 - cy;
    if (dx * dx + dy * dy <= r * r) g.set(x, y, tok);
  }
}

/** La bouche VMC, 28 × 28 : cadre vissé, carter rond, hélice à pales courbes, grille devant. */
function srvVmc({ regime = "moyen" } = {}) {
  const s = mk(28, 28), g = s.L(), M = P.metal, D = R("dalle");
  g.rect(0, 0, 28, 28, M.d); g.rect(1, 1, 26, 26, M.b); g.rect(1, 1, 26, 1, M.hi); g.rect(1, 1, 1, 26, M.hi);
  g.rect(26, 2, 1, 25, M.s); g.rect(2, 26, 25, 1, M.s);
  for (const [x, y] of [[2, 2], [24, 2], [2, 24], [24, 24]]) { g.rect(x, y, 2, 2, M.s); g.px(x, y, M.hi); }
  g.rect(4, 4, 20, 20, D.d);
  srvRond(g, 14, 14, 10, M.s); srvRond(g, 14, 14, 9, D.d);
  // L'hélice : une pale, puis ses trois copies tournées d'un quart de tour autour de (14, 14).
  const anime = regime !== "arret", duree = { lent: "2.4s", moyen: "1.2s", rapide: "0.6s" }[regime];
  const hl = s.L(anime ? "srv-helice" : "", anime ? `animation-duration:${duree}` : "");
  const pale = [[14, 5, "s"], [15, 5, "b"], [16, 5, "b"], [13, 6, "hi"], [14, 6, "hi"], [15, 6, "b"], [16, 6, "b"], [17, 6, "s"],
    [13, 7, "hi"], [14, 7, "b"], [15, 7, "b"], [16, 7, "s"], [13, 8, "hi"], [14, 8, "b"], [15, 8, "s"],
    [13, 9, "hi"], [14, 9, "b"], [15, 9, "s"], [13, 10, "hi"], [14, 10, "s"], [13, 11, "hi"], [14, 11, "s"]];
  for (let q = 0; q < 4; q++) for (const [x, y, t] of pale) {
    let u = x + .5 - 14, v = y + .5 - 14;
    for (let k = 0; k < q; k++) [u, v] = [-v, u];
    hl.set(Math.round(u + 14 - .5), Math.round(v + 14 - .5), "metal." + t);
  }
  const m = s.L(); m.rect(12, 12, 4, 4, M.s); m.rect(13, 13, 2, 2, M.d); m.px(12, 12, M.hi);
  const l = s.L("", "opacity:.6"); for (const y of [6, 10, 14, 18, 22]) l.rect(4, y, 20, 1, M.s);
  return s;
}

/** L'extincteur, 12 × 28 : poignée, manomètre, corps arrondi, étiquette, tuyau le long du flanc. */
function srvExtincteur() {
  const s = mk(12, 28), g = s.L(), M = P.metal, X = R("extincteur"), B = R("badge"), K = P.frame;
  g.rect(2, 0, 6, 1, M.hi); g.rect(3, 1, 5, 1, M.b); g.px(7, 1, M.s);
  g.rect(8, 2, 4, 2, M.b); g.rect(8, 2, 4, 1, M.hi);
  g.rect(4, 2, 4, 4, M.b); g.rect(4, 2, 1, 4, M.hi); g.rect(7, 2, 1, 4, M.s);
  g.rect(3, 6, 6, 1, X.b); g.rect(2, 7, 8, 20, X.b); g.px(3, 6, X.hi);
  g.rect(3, 7, 1, 19, X.hi); g.rect(8, 7, 1, 20, X.s); g.rect(9, 7, 1, 20, X.d);
  g.rect(2, 26, 8, 1, X.d); g.rect(3, 27, 6, 1, K.d);
  // L'étiquette, avec trois lignes de texte.
  g.rect(2, 14, 6, 6, B.b); g.rect(2, 14, 6, 1, B.hi);
  g.rect(3, 16, 4, 1, B.s); g.rect(3, 18, 3, 1, B.s); g.px(7, 19, B.d);
  // Le tuyau, de la buse au bas du corps.
  g.rect(10, 4, 2, 18, K.b); g.rect(11, 4, 1, 18, K.s); g.rect(10, 21, 1, 2, K.b); g.px(10, 4, K.hi);
  return s;
}

/** La porte coupe-feu, 28 × 36 : hublot armé, ferme-porte, béquille, barre, plaque de bas de porte, lecteur de badge. */
function srvPorte() {
  const s = mk(28, 36), g = s.L(), M = P.metal, K = P.frame, B = R("badge");
  g.rect(0, 0, 22, 36, M.d); g.rect(1, 1, 20, 35, M.s); g.rect(1, 1, 20, 1, M.b);
  g.rect(2, 2, 18, 34, M.b); g.rect(2, 2, 18, 1, M.hi); g.rect(2, 2, 1, 34, M.hi); g.rect(19, 3, 1, 33, M.s);
  for (const y of [6, 26]) { g.rect(1, y, 2, 3, M.d); g.px(2, y, M.s); }
  // Ferme-porte en haut.
  g.rect(10, 3, 8, 2, M.s); g.rect(10, 3, 8, 1, M.hi); g.px(17, 4, M.d);
  // Hublot en verre armé.
  g.rect(4, 6, 14, 6, M.d); g.rect(5, 7, 12, 4, K.b); g.rect(5, 10, 12, 1, K.s);
  for (let x = 6; x < 17; x += 3) { g.px(x, 8, K.d); g.px(x + 1, 9, K.d); }
  g.line(7, 7, 10, 10, M.hi); g.line(8, 7, 11, 10, M.s); g.line(12, 7, 13, 8, M.s);
  // Béquille.
  g.rect(16, 17, 2, 4, M.s); g.rect(12, 18, 6, 1, M.hi); g.rect(12, 19, 6, 1, M.s); g.px(16, 17, M.hi);
  // Barre antipanique, plaque de bas de porte.
  g.rect(4, 24, 14, 1, M.hi); g.rect(4, 25, 14, 1, M.d); g.rect(4, 24, 1, 2, M.s); g.rect(17, 24, 1, 2, M.s);
  g.rect(3, 31, 16, 4, M.s); g.rect(3, 31, 16, 1, M.hi); g.rect(18, 31, 1, 4, M.d);
  // Le lecteur de badge : une fente et un clavier, sans voyant.
  g.rect(22, 14, 6, 10, M.d); g.rect(23, 15, 4, 8, M.s); g.rect(23, 15, 4, 1, M.b); g.rect(23, 15, 1, 8, M.b);
  g.rect(24, 16, 2, 4, B.b); g.px(24, 16, B.hi); g.px(25, 19, B.s);
  g.px(24, 21, M.d); g.px(25, 21, M.d);
  return s;
}

/** Une dalle du faux plancher, 24 × 24 : joint, chanfrein éclairé en haut à gauche ; perforée, 16 trous creusés. */
function srvDalle(perforee) {
  const s = mk(24, 24), g = s.L(), D = R("dalle");
  g.rect(0, 0, 24, 24, D.s); g.rect(0, 0, 24, 1, D.d); g.rect(0, 0, 1, 24, D.d);
  g.rect(1, 1, 22, 22, D.b); g.rect(1, 1, 22, 1, D.hi); g.rect(1, 1, 1, 22, D.hi);
  g.rect(2, 22, 21, 1, D.s); g.rect(22, 2, 1, 21, D.s);
  if (perforee) for (const y of [6, 10, 14, 18]) for (const x of [6, 10, 14, 18]) { g.rect(x - 1, y - 1, 2, 2, D.d); g.px(x, y, D.s); }
  else [[5, 7], [15, 4], [9, 15], [18, 17], [12, 10], [4, 19]].forEach(([x, y], i) => g.px(x, y, i % 2 ? D.s : D.hi));
  return s;
}

/* ---------- Scènes d'écran, 12 × 8 ---------- */

/**
 * Une animation image par image : n calques, un seul visible à la fois. Le premier reste
 * visible sans CSS ni mouvement ; les autres sont masqués en ligne, l'animation les dévoile.
 */
function srvTrame(s, n, duree, dessin) {
  for (let i = 0; i < n; i++) {
    const style = `animation-duration:${duree}s;animation-delay:-${+(i * duree / n).toFixed(3)}s` + (i ? ";opacity:0" : "");
    dessin(s.L("srv-trame srv-trame-" + n, style), i);
  }
}

/*
 * Le fond éteint de l'écran (zinc-900 dans Ecran.tsx), sous la scène : sans lui, le contour des
 * teintes d'état comblerait les interlignes. Le liseré de nuit qu'il prend ici, seul, disparaît
 * dans le poste, où la coque de l'écran le borde.
 */
function srvEcranFond() { const s = mk(12, 8); s.L().rect(0, 0, 12, 8, "ecran-fond.b"); return s; }

/** Lignes de code indentées, motif de 8 lignes qui boucle sans saut. */
const SRV_CODE = [[0, 0, 2, "hi"], [3, 0, 4, "b"], [2, 2, 6, "b"], [2, 4, 3, "s"], [6, 4, 3, "b"], [0, 6, 4, "b"]];
function srvEcranCode({ ton = "actif", anime = true } = {}) {
  const s = srvEcranFond(), L = E(ton);
  const motif = (g, k) => { for (const [x, y, w, t] of SRV_CODE) g.rect(x, (y - k + 8) % 8, w, 1, L[t]); };
  if (anime) srvTrame(s, 8, 1.2, motif); else motif(s.L(), 0);
  return s;
}
function srvEcranLecture() {
  const s = srvEcranFond(), Pg = R("ecran-page"), g = s.L();
  g.rect(2, 0, 8, 8, Pg.b); g.rect(9, 1, 1, 7, Pg.s); g.clr(9, 0); g.px(8, 0, Pg.hi); g.px(8, 1, Pg.s);
  g.rect(3, 2, 5, 1, Pg.d); g.rect(3, 4, 4, 1, Pg.d); g.rect(3, 6, 5, 1, Pg.d);
  return s;
}
function srvEcranTests({ ton = "actif", anime = true } = {}) {
  const s = srvEcranFond(), L = E(ton), A = E("attente"), g = s.L();
  g.rect(0, 2, 12, 4, A.d);
  const barre = (b, w) => { b.rect(0, 2, w, 4, L.b); b.rect(0, 2, w, 1, L.hi); b.rect(0, 5, w, 1, L.s); };
  if (anime) srvTrame(s, 6, 1.8, (b, i) => barre(b, 2 + i * 2)); else barre(s.L(), 6);
  return s;
}
function srvEcranAudit({ ton = "actif", anime = true } = {}) {
  const s = srvEcranFond(), L = E(ton), A = E("attente"), g = s.L();
  [[0, 0, 10], [0, 2, 12], [2, 4, 7], [0, 6, 11]].forEach(([x, y, w]) => g.rect(x, y, w, 1, A.d));
  const ligne = (b, y) => { b.rect(0, y, 12, 1, L.hi); b.rect(0, y + 1, 12, 1, L.b); };
  if (anime) srvTrame(s, 8, 1.2, ligne); else ligne(s.L(), 2);
  return s;
}
function srvEcranDiff({ anime = true } = {}) {
  const s = srvEcranFond(), g = s.L(anime ? "lueur" : ""), V = E("fait"), Ro = E("blocage");
  [[V, 8], [Ro, 6], [V, 10], [Ro, 4]].forEach(([T, w], i) => { g.px(0, i * 2, T.hi); g.rect(2, i * 2, w, 1, T.b); });
  return s;
}
function srvEcranCriteres({ ton = "actif", anime = true } = {}) {
  const s = srvEcranFond(), L = E(ton), Pg = R("ecran-page"), g = s.L(anime ? "lueur" : "");
  [[0, 7], [3, 9], [6, 5]].forEach(([y, w]) => {
    g.rect(0, y, 2, 2, Pg.b); g.px(1, y + 1, Pg.s);
    g.rect(3, y, w, 1, L.b);
  });
  return s;
}
function srvEcranOk() {
  const s = srvEcranFond(), V = E("fait"), g = s.L();
  g.line(1, 4, 3, 6, V.s); g.line(3, 6, 9, 0, V.s);
  g.line(1, 3, 3, 5, V.b); g.line(3, 5, 8, 0, V.b); g.px(8, 0, V.hi); g.px(1, 3, V.hi);
  return s;
}
function srvEcranKo() {
  const s = srvEcranFond(), Ro = E("blocage"), g = s.L();
  g.line(3, 0, 10, 7, Ro.s); g.line(10, 0, 3, 7, Ro.s);
  g.line(2, 0, 9, 7, Ro.b); g.line(9, 0, 2, 7, Ro.b); g.px(2, 0, Ro.hi);
  return s;
}

/* ---------- Registre ---------- */

enregistrer({ id: "petite-baie", nom: "Petite baie, trois services", fichier: "Baie", salle: "run", grille: "12 × 14 → 24 × 28", dw: 36, dh: 42,
  avant: () => avantPetiteBaie(), apres: () => srvPetiteBaie(),
  note: "Chaque étage devient un serveur 2U : voyant dans son logement, grille d'aération, trois tiroirs de disques. De haut en bas : en cours, échoué, arrêté." });
enregistrer({ id: "chemin-de-cables", nom: "Chemin de câbles (tronçon)", fichier: "CheminDeCables", salle: "serveurs", grille: "40 × 8 → 80 × 16 (tronçon de 200 × 8)", dw: 120, dh: 24,
  avant: () => avantChemin(), apres: () => srvChemin(),
  note: "Un caillebotis à fils avec des câbles couchés visibles entre les barreaux, et une boucle qui pend sous le chemin. Le tronçon de 80 se répète sans couture." });
enregistrer({ id: "bouche-vmc", nom: "Bouche VMC, régime moyen", fichier: "BoucheVMC", salle: "serveurs", grille: "14 × 14 → 28 × 28", dw: 42, dh: 42,
  avant: () => avantVmc(), apres: () => srvVmc(), variante: { label: "Arrêtée", f: () => srvVmc({ regime: "arret" }) },
  note: "Cadre vissé, carter rond, hélice à pales courbes qui tourne au régime de la mémoire (2,4 s, 1,2 s ou 0,6 s le quart de tour). La croix d'avant, tournée de 90°, se ressemblait : les pales courbes rendent la rotation visible." });
enregistrer({ id: "extincteur", nom: "Extincteur", fichier: "Extincteur", salle: "serveurs", grille: "6 × 14 → 12 × 28", dw: 18, dh: 42,
  avant: () => avantExtincteur(), apres: () => srvExtincteur(),
  note: "Corps arrondi en volume, poignée et buse en métal, étiquette avec lignes de texte, tuyau noir le long du flanc." });
enregistrer({ id: "porte-coupe-feu", nom: "Porte coupe-feu", fichier: "PorteCoupeFeu", salle: "serveurs", grille: "14 × 18 → 28 × 36", dw: 42, dh: 54,
  avant: () => avantPorte(), apres: () => srvPorte(),
  note: "Un hublot en verre armé avec un reflet, un ferme-porte, des gonds, une béquille, une barre antipanique et une plaque de bas de porte. Le lecteur de badge gagne une fente et un clavier, toujours sans voyant." });
enregistrer({ id: "dalle-perforee", nom: "Dalle perforée", fichier: "DallePerforee", salle: "serveurs", grille: "12 × 12 → 24 × 24", dw: 36, dh: 36,
  avant: () => avantDalle(true), apres: () => srvDalle(true),
  note: "Un chanfrein éclairé en haut à gauche et des trous creusés, ombrés du côté de la lumière." });
enregistrer({ id: "dalle-pleine", nom: "Dalle pleine", fichier: "DallePleine", salle: "serveurs", grille: "12 × 12 → 24 × 24", dw: 36, dh: 36,
  avant: () => avantDalle(false), apres: () => srvDalle(false),
  note: "Le même chanfrein que la dalle perforée, et quelques grains de revêtement pour que le sol ne soit pas un aplat." });

const SRV_SCENES = [
  { id: "code", nom: "code qui défile", apres: () => srvEcranCode(), variante: { label: "Immobile", f: () => srvEcranCode({ anime: false }) },
    note: "Des lignes indentées de longueurs variées, mot-clé plus clair en tête. Le défilement passe à huit paliers d'une ligne au lieu de quatre de deux, en image par image : rien ne déborde de l'écran." },
  { id: "lecture", nom: "page lue", apres: () => srvEcranLecture(),
    note: "La page a un coin corné et trois lignes de texte au lieu de deux. Jamais animée." },
  { id: "tests", nom: "barre de tests", apres: () => srvEcranTests(), variante: { label: "Immobile (mi-course)", f: () => srvEcranTests({ anime: false }) },
    note: "Une barre en relief dans une gouttière, qui avance en six paliers ; immobile, elle reste à mi-course comme avant." },
  { id: "audit", nom: "balayage d'audit", apres: () => srvEcranAudit(), variante: { label: "Immobile", f: () => srvEcranAudit({ anime: false }) },
    note: "Quatre lignes de texte de longueurs différentes sous une ligne de balayage à reflet, qui descend en huit paliers." },
  { id: "diff", nom: "diff", apres: () => srvEcranDiff(), variante: { label: "Immobile", f: () => srvEcranDiff({ anime: false }) },
    note: "Chaque ligne gagne un repère en marge (le + ou le −), plus clair que le texte. Vert et rouge restent des teintes d'état." },
  { id: "criteres", nom: "critères", apres: () => srvEcranCriteres(), variante: { label: "En question", f: () => srvEcranCriteres({ ton: "question" }) },
    note: "Trois critères au lieu de deux, chacun avec sa case en relief." },
  { id: "ok", nom: "verdict favorable", apres: () => srvEcranOk(),
    note: "La coche à épaisseur de deux pixels, avec un reflet en bout de trait." },
  { id: "ko", nom: "verdict défavorable", apres: () => srvEcranKo(),
    note: "La croix à épaisseur de deux pixels, centrée dans l'écran." },
];
for (const sc of SRV_SCENES) enregistrer({
  id: "ecran-" + sc.id, nom: "Écran de poste, " + sc.nom, fichier: "EcranScenes", salle: "run", grille: "6 × 4 → 12 × 8", dw: 21, dh: 14,
  avant: () => avantEcran(sc.id), apres: sc.apres, variante: sc.variante, note: sc.note,
});
