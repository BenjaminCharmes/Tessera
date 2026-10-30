"use strict";
/* Têtes, postes, agents debout. Grille ×2 des composants Tete, PersonnageAssis, PersonnageDebout, Poste, Ecran. */

/** La tête : visage 12 × 9 en (x, y), cheveux au-dessus. `expr` suit la santé de l'agent. */
function tete(g, x, y, ph, expr = "neutre") {
  const H = P.hair[ph.cheveux - 1], K = P.skin[ph.peau - 1], ink = P.ink, br = H.s;
  g.rect(x - 1, y + 4, 1, 2, K.s); g.rect(x + 12, y + 4, 1, 2, K.s);
  g.rect(x, y, 12, 9, K.b); g.rect(x + 11, y + 1, 1, 7, K.s); g.rect(x + 1, y + 8, 10, 1, K.s); g.clr(x, y + 8); g.clr(x + 11, y + 8);
  g.rect(x + 1, y + 1, 1, 3, K.hi);
  if (ph.coiffure === "long") { g.rect(x - 2, y - 1, 2, 13, H.b); g.rect(x + 12, y - 1, 2, 13, H.s); g.rect(x - 2, y + 11, 2, 1, H.s); g.rect(x + 12, y + 11, 2, 1, H.d); }
  if (ph.coiffure === "carre") { g.rect(x - 2, y - 1, 2, 8, H.b); g.rect(x + 12, y - 1, 2, 8, H.s); g.rect(x - 2, y + 6, 2, 1, H.s); }
  if (ph.coiffure === "chauve") {
    g.rect(x + 1, y - 2, 10, 2, K.b); g.rect(x, y - 1, 12, 1, K.b); g.rect(x + 3, y - 2, 3, 1, K.hi); g.rect(x + 9, y - 1, 2, 1, K.s);
    g.rect(x - 1, y + 1, 2, 4, H.b); g.rect(x + 11, y + 1, 2, 4, H.s);
  } else {
    g.rect(x + 1, y - 3, 10, 1, H.b); g.rect(x, y - 2, 12, 2, H.b); g.rect(x, y, 12, 1, H.b);
    g.px(x + 2, y + 1, H.b); g.px(x + 3, y + 1, H.b); g.px(x + 7, y + 1, H.b); g.px(x + 10, y + 1, H.s);
    g.rect(x + 9, y - 2, 3, 3, H.s); g.rect(x + 3, y - 2, 3, 1, H.hi); g.px(x + 2, y - 1, H.hi);
    if (ph.coiffure === "court") { g.rect(x, y, 1, 3, H.b); g.rect(x + 11, y, 1, 3, H.s); }
  }
  const yeux = (dx = 0) => { g.rect(x + 3 + dx, y + 4, 1, 2, ink); g.rect(x + 8 + dx, y + 4, 1, 2, ink); };
  const joues = () => { g.px(x + 2, y + 6, K.bl); g.px(x + 9, y + 6, K.bl); };
  switch (expr) {
    case "actif": g.rect(x + 2, y + 3, 2, 1, br); g.rect(x + 8, y + 3, 2, 1, br); yeux(1); g.rect(x + 5, y + 7, 2, 1, K.d); break;
    case "attente": g.rect(x + 2, y + 5, 2, 1, ink); g.rect(x + 8, y + 5, 2, 1, ink); g.px(x + 6, y + 7, K.d); joues(); break;
    case "question": g.rect(x + 2, y + 3, 2, 1, br); g.rect(x + 8, y + 2, 2, 1, br); yeux(); g.px(x + 6, y + 7, ink); joues(); break;
    case "blocage": g.px(x + 2, y + 2, br); g.px(x + 3, y + 3, br); g.px(x + 9, y + 2, br); g.px(x + 8, y + 3, br); yeux();
      g.rect(x + 4, y + 7, 4, 1, K.d); g.px(x + 13, y + 1, P.sueur.hi); g.rect(x + 12, y + 2, 2, 2, P.sueur.b); break;
    case "fait": [[2, 5], [3, 4], [4, 5], [7, 5], [8, 4], [9, 5]].forEach(([a, b]) => g.px(x + a, y + b, ink));
      g.px(x + 4, y + 6, K.d); g.rect(x + 5, y + 7, 2, 1, K.d); g.px(x + 7, y + 6, K.d); joues(); break;
    default: g.rect(x + 2, y + 3, 2, 1, br); g.rect(x + 8, y + 3, 2, 1, br); yeux(); g.rect(x + 5, y + 7, 2, 1, K.d); joues();
  }
}
/** Ce qui distingue une tenue : capuche à cordons du codeur, col et cravate du reviewer. */
function torseDetails(g, role, x, y) {
  const T = P.top[role];
  if (role === "codeur") { g.rect(x + 3, y, 8, 2, T.s); g.rect(x + 4, y, 6, 1, T.d); g.rect(x + 5, y + 2, 1, 3, T.hi); g.rect(x + 8, y + 2, 1, 2, T.hi); g.rect(x + 3, y + 5, 8, 2, T.s); }
  if (role === "reviewer") { g.rect(x + 4, y, 2, 1, P.col.b); g.rect(x + 8, y, 2, 1, P.col.s); g.rect(x + 6, y, 2, 2, P.cravate.hi); g.rect(x + 6, y + 2, 2, 5, P.cravate.b); g.px(x + 7, y + 7, P.cravate.b); }
}
/** La santé → l'expression du visage. */
const EXPR = { actif: "actif", attente: "attente", question: "question", blocage: "blocage", fait: "fait" };

/** Le poste, grille 40 × 36. Calques : 0 chaise, 1 agent, 2 bureau, 3 mains, 4 écran, 5 lueur. */
function poste({ role = "codeur", ph = PH.codeur, etat = "actif", vide = false } = {}) {
  const s = mk(40, 36), T = P.top[role], K = P.skin[ph.peau - 1];
  const ch = s.L(); ch.rect(6, 13, 18, 11, P.chair.s); ch.rect(7, 12, 16, 1, P.chair.b); ch.rect(7, 13, 16, 1, P.chair.hi);
  const g = s.L();
  if (!vide) {
    tete(g, 9, 6, ph, EXPR[etat]);
    g.rect(13, 15, 4, 1, K.s);
    g.rect(8, 16, 14, 8, T.b); g.rect(7, 17, 16, 7, T.b); g.rect(19, 17, 4, 7, T.s); g.rect(8, 17, 4, 1, T.hi); g.px(8, 18, T.hi);
    torseDetails(g, role, 8, 16);
  } else { ch.rect(6, 20, 18, 4, P.chair.b); ch.rect(6, 20, 18, 1, P.chair.hi); }
  const d = s.L();
  d.rect(10, 23, 10, 1, P.clavier.hi);
  d.rect(2, 24, 36, 1, P.desk.hi); d.rect(2, 25, 36, 2, P.desk.b); d.rect(2, 27, 36, 1, P.desk.s);
  d.rect(4, 28, 2, 8, P.desk.s); d.rect(34, 28, 2, 8, P.desk.s); d.rect(4, 28, 2, 1, P.desk.d); d.rect(34, 28, 2, 1, P.desk.d);
  const a = s.L(etat === "actif" && !vide ? "tape" : "");
  if (!vide) {
    a.rect(5, 18, 3, 5, T.s); a.rect(22, 18, 3, 5, T.s); a.rect(5, 18, 1, 4, T.d);
    a.rect(5, 22, 3, 2, K.b); a.rect(22, 22, 3, 2, K.b); a.px(7, 23, K.s); a.px(24, 23, K.s);
  }
  const e = s.L();
  e.rect(24, 10, 16, 12, P.frame.b); e.rect(24, 10, 16, 1, P.frame.hi); e.rect(24, 11, 1, 10, P.frame.hi);
  e.rect(39, 11, 1, 11, P.frame.s); e.rect(25, 21, 15, 1, P.frame.s);
  e.rect(31, 22, 2, 1, P.frame.s); e.rect(28, 23, 8, 1, P.frame.b);
  const L = E(vide ? "attente" : etat), l = s.L(etat === "actif" && !vide ? "lueur" : "");
  l.rect(26, 12, 12, 8, L.d);
  if (vide) l.rect(26, 12, 12, 8, "cadre.d");
  else if (etat === "attente") l.rect(30, 15, 4, 2, L.s);
  else if (etat === "fait") { l.px(29, 16, L.hi); l.px(30, 17, L.hi); l.px(31, 18, L.hi); l.px(32, 17, L.hi); l.px(33, 16, L.hi); l.px(34, 15, L.hi); l.px(35, 14, L.hi); }
  else {
    l.rect(27, 13, 5, 1, L.hi); l.rect(33, 13, 3, 1, L.b); l.rect(28, 15, 7, 1, L.b); l.rect(28, 17, 4, 1, L.b);
    l.rect(33, 17, 2, 1, L.hi); l.rect(27, 19, 3, 1, L.s); l.px(37, 12, L.hi);
  }
  return s;
}
/** La nuit, l'écran éclaire l'agent et ses mains (calques 1 et 3), en trois paliers. */
function eclairer(s, etat, cx = 32, cy = 16) {
  for (const k of [1, 3]) {
    const g = s.layers[k].g;
    g.p = g.p.map((c, i) => {
      if (!c) return c;
      const x = i % s.w, y = Math.floor(i / s.w), d = Math.hypot(x - cx, (y - cy) * 1.3);
      const n = d < 12 ? 3 : d < 16 ? 2 : d < 20 ? 1 : 0;
      return n ? `${c}^${etat}^${n}` : c;
    });
  }
  return s;
}
/** Même grille que l'actuel (20 × 18), ombrage seulement. */
function posteMemeGrille({ role = "codeur", ph = PH.codeur, etat = "actif" } = {}) {
  const s = mk(20, 18), g = s.L(), T = P.top[role], K = P.skin[ph.peau - 1], H = P.hair[ph.cheveux - 1];
  g.rect(5, 1, 6, 2, H.b); g.rect(9, 1, 2, 2, H.s); g.px(6, 1, H.hi);
  g.rect(5, 3, 6, 4, K.b); g.rect(10, 4, 1, 3, K.s); g.clr(5, 6); g.clr(10, 6); g.rect(5, 3, 1, 1, H.b); g.rect(10, 3, 1, 1, H.s);
  g.px(6, 4, P.ink); g.px(9, 4, P.ink);
  g.rect(4, 7, 8, 5, T.b); g.rect(9, 8, 3, 4, T.s); g.clr(4, 7); g.clr(11, 7); g.rect(6, 7, 4, 1, T.s); g.px(5, 8, T.hi);
  const a = s.L(etat === "actif" ? "tape" : ""); a.rect(3, 9, 2, 2, T.s); a.rect(11, 9, 2, 2, T.s); a.rect(3, 11, 2, 1, K.b); a.rect(11, 11, 2, 1, K.b);
  const d = s.L(); d.rect(1, 12, 18, 1, P.desk.hi); d.rect(1, 13, 18, 1, P.desk.s); d.rect(2, 14, 1, 4, P.desk.s); d.rect(17, 14, 1, 4, P.desk.s);
  d.rect(12, 5, 8, 6, P.frame.b); d.rect(12, 5, 8, 1, P.frame.hi); d.rect(15, 11, 2, 1, P.frame.s);
  const L = E(etat), l = s.L(etat === "actif" ? "lueur" : ""); l.rect(13, 6, 6, 4, L.d); l.rect(14, 7, 3, 1, L.hi); l.rect(14, 8, 4, 1, L.b);
  return s;
}
/** L'agent debout, grille 24 × 40 : tasse, mains vides, bras levés ; `legs`/`bob`/`swing` pour la marche. */
function debout({ role = "reviewer", ph = PH.reviewer, expr = "fait", tasse = true, brasLeves = false, legs = 0, bob = 0, swing = 0 } = {}) {
  const s = mk(24, 40), g = s.L(), T = P.top[role], K = P.skin[ph.peau - 1];
  const la = legs === 1 ? 2 : 0, lb = legs === -1 ? 2 : 0;
  if (ph.jupe) {
    g.rect(5, 32 + bob, 2, 6 - la - bob, K.b); g.rect(13, 32 + bob, 2, 6 - lb - bob, K.s);
    g.rect(4, 38 - la, 4, 2, P.shoe.b); g.rect(12, 38 - lb, 4, 2, P.shoe.b);
    g.rect(2, 25 + bob, 16, 7, T.s); g.rect(2, 31 + bob, 16, 1, T.d); g.rect(14, 26 + bob, 4, 5, T.d);
  } else {
    const Pn = P.pants;
    g.rect(4, 26 + bob, 4, 12 - la - bob, Pn.b); g.rect(7, 26 + bob, 1, 12 - la - bob, Pn.s);
    g.rect(12, 26 + bob, 4, 12 - lb - bob, Pn.b); g.rect(15, 26 + bob, 1, 12 - lb - bob, Pn.s);
    g.rect(3, 38 - la, 5, 2, P.shoe.b); g.rect(3, 38 - la, 5, 1, P.shoe.hi); g.rect(12, 38 - lb, 5, 2, P.shoe.b); g.rect(12, 38 - lb, 5, 1, P.shoe.hi);
    g.rect(2, 25 + bob, 16, 1, Pn.d);
  }
  tete(g, 4, 3 + bob, ph, expr);
  g.rect(8, 12 + bob, 4, 1, K.s);
  g.rect(3, 13 + bob, 14, 12, T.b); g.rect(2, 14 + bob, 16, 11, T.b); g.rect(14, 14 + bob, 4, 11, T.s); g.rect(3, 14 + bob, 3, 1, T.hi);
  torseDetails(g, role, 5, 13 + bob);
  if (brasLeves) {
    g.rect(0, 4, 2, 10, T.s); g.rect(0, 2, 2, 2, K.b); g.rect(18, 4, 2, 10, T.s); g.rect(18, 2, 2, 2, K.b);
    return s;
  }
  g.rect(0, 14 + bob + swing, 2, 10, T.s); g.rect(0, 14 + bob + swing, 1, 9, T.d); g.rect(0, 24 + bob + swing, 2, 2, K.b);
  if (tasse) {
    g.rect(18, 14 + bob, 2, 5, T.s); g.rect(19, 19 + bob, 3, 2, K.b);
    g.rect(19, 15 + bob, 3, 4, P.cup.b); g.rect(19, 15 + bob, 3, 1, P.cup.hi); g.px(20, 15 + bob, P.coffee); g.rect(22, 16 + bob, 1, 2, P.cup.s); g.rect(21, 16 + bob, 1, 3, P.cup.s);
  } else { g.rect(18, 14 + bob - swing, 2, 10, T.s); g.rect(18, 24 + bob - swing, 2, 2, K.b); }
  return s;
}
const MARCHE = [{ legs: 0 }, { legs: 1, bob: 1, swing: 1 }, { legs: 0 }, { legs: -1, bob: 1, swing: -1 }];

enregistrer({ id: "poste", nom: "Poste, agent qui tape", fichier: "Poste + PersonnageAssis + Tete + Ecran", salle: "run", grille: "20 × 18 → 40 × 36", dw: 70, dh: 63,
  avant: () => avantPoste(), apres: () => poste(), meme: () => posteMemeGrille(), lumiere: "actif",
  note: "Mains sur le clavier, yeux tournés vers l'écran pendant qu'il travaille, dossier de chaise, code qui s'allume à l'écran. Le sweat à capuche du codeur a ses cordons." });
enregistrer({ id: "poste-rev", nom: "Poste, reviewer en attente", fichier: "même composant, autre rôle et autre santé", salle: "run", grille: "20 × 18 → 40 × 36", dw: 70, dh: 63,
  avant: () => avantPoste("reviewer", "attente"), apres: () => poste({ role: "reviewer", ph: PH.reviewer, etat: "attente" }), meme: () => posteMemeGrille({ role: "reviewer", ph: PH.reviewer, etat: "attente" }), lumiere: "attente",
  note: "Santé « attente » : les yeux se ferment, l'écran se met en veille. Cheveux longs, col et cravate." });
enregistrer({ id: "debout", nom: "Agent debout, tasse à la main", fichier: "PersonnageDebout", salle: "run", grille: "12 × 20 → 24 × 40", dw: 42, dh: 70,
  avant: () => avantDebout(), apres: () => debout(),
  note: "Il a fini : il sourit. La tasse a une anse et du café, les chaussures se distinguent du pantalon, la ceinture marque la taille." });
