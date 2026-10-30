"use strict";
/* Le rendu d'une entrée du registre, commun aux pages. */

const resolveurs = new Map();
/** Un résolveur par mode et par jeu de choix de jour, gardé tant que les choix ne changent pas. */
function res(mode, choix = {}) {
  const k = mode + JSON.stringify(choix);
  if (!resolveurs.has(k)) resolveurs.set(k, resolveur(mode, choix));
  return resolveurs.get(k);
}
/** Les familles de couleur qu'un sprite emploie, états exclus. */
function famillesDe(s) {
  const f = new Set();
  for (const l of s.layers) for (const t of l.g.p) if (t && !t.startsWith("#")) { const fam = t.split(".")[0]; if (!fam.startsWith("etat-")) f.add(fam); }
  return f;
}
/**
 * Dessine `def` : quoi = avant | apres | meme | variante ; mode = jour | nuit.
 * La nuit, un poste reçoit la lueur de son écran (`def.lumiere`).
 */
function rendre(def, { quoi = "apres", mode = "jour", zoom = 1, outline = true, choix = {}, echelle = 1 } = {}) {
  const fn = { avant: def.avant, apres: def.apres, meme: def.meme, variante: def.variante && def.variante.f }[quoi];
  const dw = def.dw * zoom * echelle, dh = def.dh * zoom * echelle;
  let s = fn();
  if (quoi === "avant") return { ...toSvg(s, dw, dh, t => t), rects: rectCount(s) };
  const familles = famillesDe(s);
  s = bake(s, def.tuile ? { outline: false, rim: false } : { outline, rim: true });
  if (mode === "nuit" && def.lumiere) eclairer(s, def.lumiere);
  return { ...toSvg(s, dw, dh, res(mode, choix)), familles };
}
const solDe = (mode, choix) => res(mode, choix)("sol.b");
