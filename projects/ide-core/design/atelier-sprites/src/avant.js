"use strict";
/*
 * Copies fidèles des sprites actuels de Tessera (frontend/src/design/bureau), au
 * rectangle près, avec leurs couleurs d'aujourd'hui (jetons --sprite-* et familles Tailwind).
 */
const C = {
  z900: "#18181b", z800: "#27272a", z700: "#3f3f46", z600: "#52525b", z500: "#71717a", z200: "#e4e4e7",
  peau: ["#f1c7a3", "#e8b98f", "#c68b59", "#8d5a3b", "#5c3a24"],
  cheveux: ["#3f2a1d", "#111827", "#a16207", "#7c2d12", "#d4d4d8", "#1c1917"],
  haut: { codeur: "#8e51ff", reviewer: "#0f766e", testeur: "#e4e4e7", securite: "#1e3a8a", validateur: "#b45309", architect: "#be185d" },
  ombre: { codeur: "#7008e7", reviewer: "#115e59", testeur: "#a1a1aa", securite: "#172554", validateur: "#92400e", architect: "#9d174d" },
  col: "#e4e4e7", cravate: "#1f2937", metal: "#52525b", metalO: "#3f3f46", metalC: "#71717a",
  plante: "#16a34a", planteO: "#15803d", pot: "#92400e", cactus: "#4d7c0f", potClair: "#d6a77a",
  machine: "#52525b", machineO: "#3f3f46", tasse: "#e4e4e7", table: "#8a6a4a", tableO: "#6b5038",
  livres: ["#9f1239", "#1e40af", "#ca8a04"], sol: "#2a2420", mur: "#3a3430", plinthe: "#1c1917",
};
const ETAT_AVANT = { actif: "#60a5fa", attente: "#71717a", question: "#fbbf24", blocage: "#f87171", fait: "#4ade80" };

function avantTete(g, ph, x, y) {
  const H = C.cheveux[ph.cheveux - 1], K = C.peau[ph.peau - 1];
  if (ph.coiffure === "long") { g.rect(x - 1, y - 1, 1, 7, H); g.rect(x + 6, y - 1, 1, 7, H); }
  if (ph.coiffure === "carre") { g.rect(x - 1, y - 1, 1, 4, H); g.rect(x + 6, y - 1, 1, 4, H); }
  if (ph.coiffure === "chauve") { g.rect(x, y - 1, 1, 2, H); g.rect(x + 5, y - 1, 1, 2, H); } else g.rect(x, y - 2, 6, 2, H);
  g.rect(x, y, 6, 4, K);
  if (ph.coiffure === "court") { g.rect(x, y, 1, 1, H); g.rect(x + 5, y, 1, 1, H); }
  if (ph.coiffure === "chauve") g.rect(x + 1, y - 1, 4, 1, K);
  g.rect(x + 1, y + 1, 1, 1, C.z900); g.rect(x + 4, y + 1, 1, 1, C.z900);
}
function avantPoste(role = "codeur", etat = "actif") {
  const ph = PH[role], s = mk(20, 18), g = s.L(), O = C.ombre[role];
  avantTete(g, ph, 5, 3);
  g.rect(4, 7, 8, 5, C.haut[role]);
  if (role === "reviewer") { g.rect(7, 7, 2, 1, C.col); g.rect(7, 8, 2, 3, C.cravate); }
  if (role === "codeur") g.rect(6, 7, 4, 1, O);
  const a = s.L(etat === "actif" ? "tape" : ""); a.rect(3, 9, 2, 3, O); a.rect(11, 9, 2, 3, O);
  const d = s.L(); d.rect(1, 12, 18, 2, C.z600); d.rect(2, 14, 1, 4, C.z700); d.rect(17, 14, 1, 4, C.z700); d.rect(12, 5, 8, 6, C.z800);
  s.L(etat === "actif" ? "lueur" : "").rect(13, 6, 6, 4, ETAT_AVANT[etat]);
  s.L().rect(15, 11, 2, 1, C.z800);
  return s;
}
function avantDebout(role = "reviewer") {
  const ph = PH[role], s = mk(12, 20), g = s.L(), O = C.ombre[role];
  avantTete(g, ph, 2, 2);
  g.rect(1, 6, 8, 7, C.haut[role]);
  if (role === "reviewer") { g.rect(4, 6, 2, 1, C.col); g.rect(4, 7, 2, 4, C.cravate); }
  g.rect(2, 13, 2, 7, C.z700); g.rect(6, 13, 2, 7, C.z700);
  g.rect(0, 7, 1, 5, O); g.rect(9, 7, 1, 3, O); g.rect(10, 6, 2, 2, C.z200);
  return s;
}
function avantBaie(etat = "actif") {
  const s = mk(12, 30), g = s.L();
  g.rect(0, 0, 12, 30, C.metalO); g.rect(1, 1, 10, 28, C.metal); g.rect(2, 2, 8, 3, C.metalO);
  g.rect(8, 3, 1, 1, ETAT_AVANT[etat]);
  for (const y of [7, 10, 13, 16, 19, 22, 25]) g.rect(2, y, 8, 1, C.metalO);
  g.rect(9, 27, 1, 1, C.metalC);
  return s;
}
function avantClim() {
  const s = mk(16, 22), g = s.L();
  g.rect(0, 0, 16, 22, C.metalO); g.rect(1, 1, 14, 20, C.metal); g.rect(2, 2, 12, 13, C.metalO);
  for (const y of [3, 5, 7, 9, 11, 13]) g.rect(3, y, 10, 1, C.metalC);
  g.rect(2, 17, 12, 3, C.metalC); g.rect(3, 18, 10, 1, C.metalO);
  return s;
}
function avantPlante(esp) {
  const s = mk(8, esp === "ficus" ? 16 : 10), g = s.L();
  if (esp === "pot") { g.rect(1, 2, 2, 2, C.plante); g.rect(5, 1, 2, 3, C.plante); g.rect(3, 0, 2, 5, C.planteO); g.rect(2, 4, 4, 1, C.planteO); g.rect(2, 5, 4, 1, C.pot); g.rect(2, 6, 4, 4, C.pot); }
  if (esp === "cactus") { g.rect(3, 0, 2, 6, C.cactus); g.rect(1, 2, 1, 2, C.cactus); g.rect(1, 3, 2, 1, C.cactus); g.rect(6, 1, 1, 3, C.cactus); g.rect(5, 3, 2, 1, C.cactus); g.rect(2, 6, 4, 4, C.potClair); }
  if (esp === "ficus") { g.rect(1, 1, 6, 5, C.plante); g.rect(2, 0, 4, 1, C.plante); g.rect(0, 3, 1, 2, C.planteO); g.rect(7, 2, 1, 3, C.planteO); g.rect(2, 4, 2, 2, C.planteO); g.rect(3, 6, 1, 5, C.pot); g.rect(2, 11, 4, 5, C.pot); }
  return s;
}
function avantMachine() {
  const s = mk(12, 16), g = s.L();
  g.rect(1, 0, 10, 14, C.machine); g.rect(1, 12, 10, 2, C.machineO); g.rect(3, 2, 6, 3, C.machineO); g.rect(5, 6, 2, 2, C.machineO);
  g.rect(4, 9, 4, 3, C.tasse); g.rect(0, 14, 12, 2, C.machineO);
  return s;
}
const RANGEES_AVANT = [
  { y: 2, livres: [[2, 0, 2, 4, 1], [4, 1, 2, 3, 2], [6, 0, 1, 4, 3], [8, 1, 2, 3, 1], [11, 0, 2, 4, 3]] },
  { y: 7, livres: [[2, 1, 1, 3, 3], [3, 0, 2, 4, 2], [5, 0, 1, 4, 1], [7, 2, 3, 2, 3], [11, 1, 1, 3, 2], [12, 0, 2, 4, 1]] },
  { y: 12, livres: [[2, 0, 2, 4, 2], [5, 1, 1, 3, 1], [6, 0, 2, 4, 3], [9, 1, 2, 3, 2], [12, 0, 1, 4, 1]] },
];
function avantBiblio() {
  const s = mk(16, 18), g = s.L();
  g.rect(0, 0, 16, 18, C.tableO); g.rect(1, 1, 14, 16, C.table);
  for (const { y, livres } of RANGEES_AVANT) { for (const [x, dy, w, h, t] of livres) g.rect(x, y + dy, w, h, C.livres[t - 1]); g.rect(1, y + 4, 14, 1, C.tableO); }
  return s;
}
