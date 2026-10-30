"use strict";
/*
 * Les familles de couleur, une base par source. Le jour prend, famille par famille,
 * la base « tessera » ou « chaud » (choix de Benjamin, cas par cas) ; la nuit prend
 * toujours « neon ». Une famille sans « chaud » ou sans « neon » retombe sur « tessera ».
 * `doux` (0 à 1) resserre la rampe d'une famille de grande surface (sol, mur).
 * Dans Tessera, chaque famille × ton deviendrait une variable --sprite-<famille>-<ton>,
 * redéfinie sous [data-moment="nuit"] : changer d'heure ne coûte que des variables CSS.
 */
const FAMILLES = {
  // Personnages
  peau1: { tessera: "#f1c7a3" }, peau2: { tessera: "#e8b98f" }, peau3: { tessera: "#c68b59" },
  peau4: { tessera: "#8d5a3b" }, peau5: { tessera: "#5c3a24" },
  cheveux1: { tessera: "#3f2a1d" }, cheveux2: { tessera: "#111827" }, cheveux3: { tessera: "#a16207" },
  cheveux4: { tessera: "#7c2d12" }, cheveux5: { tessera: "#d4d4d8" }, cheveux6: { tessera: "#1c1917" },
  "haut-codeur": { tessera: "#8e51ff" }, "haut-reviewer": { tessera: "#0f766e" },
  "haut-testeur": { tessera: "#e4e4e7", chaud: "#e9e2d0" }, "haut-securite": { tessera: "#1e3a8a", chaud: "#2a4a9a" },
  "haut-validateur": { tessera: "#b45309" }, "haut-architect": { tessera: "#be185d" },
  "haut-resolveur": { tessera: "#c2410c" }, "haut-doc-technique": { tessera: "#0e7490" }, "haut-doc-fonctionnelle": { tessera: "#4d7c0f" },
  pantalon: { tessera: "#3f3f46", chaud: "#3d3a55", neon: "#26284a" },
  chaussure: { tessera: "#27272a", chaud: "#2b2230", neon: "#14152b" },
  col: { tessera: "#e4e4e7" }, cravate: { tessera: "#1f2937" }, encre: { tessera: "#18181b" },
  sueur: { tessera: "#93c5fd" },
  // Postes
  bureau: { tessera: "#52525b", chaud: "#a0703f", neon: "#2a2c4a" },
  chaise: { tessera: "#2f2f35", chaud: "#5a3b2a", neon: "#1c1d36" },
  cadre: { tessera: "#2a2a30", chaud: "#3b3440", neon: "#14152b" },
  clavier: { tessera: "#71717a", chaud: "#8a8f9a", neon: "#3a3f66" },
  // Matières
  metal: { tessera: "#52525b", chaud: "#6b6f7a", neon: "#2d3150" },
  bois: { tessera: "#8a6a4a", chaud: "#9a6a3a", neon: "#3a2f5a" },
  plante: { tessera: "#16a34a", chaud: "#3fa34d", neon: "#18b88a" },
  pot: { tessera: "#a14a17", chaud: "#c0602f", neon: "#5a3d8a" },
  terre: { tessera: "#4a2c17", chaud: "#5a3420", neon: "#24183a" },
  cactus: { tessera: "#4d7c0f", chaud: "#5f8a1e", neon: "#1fa37a" },
  "pot-clair": { tessera: "#d6a77a", chaud: "#e0b48a", neon: "#7a5ab8" },
  epine: { tessera: "#ecfccb" }, fleur: { tessera: "#f472b6", neon: "#ff5fd2" },
  machine: { tessera: "#52525b", chaud: "#8c3b2f", neon: "#2a2c4a" },
  tasse: { tessera: "#e4e4e7", chaud: "#f2ead8", neon: "#cfd3ff" },
  cafe: { tessera: "#5b3a1e" },
  livre1: { tessera: "#9f1239", chaud: "#b8323e", neon: "#ff3d8b" },
  livre2: { tessera: "#1e40af", chaud: "#2f5fa8", neon: "#3dd6ff" },
  livre3: { tessera: "#ca8a04", chaud: "#d9a23a", neon: "#ffd23d" },
  // Pièce
  mur: { tessera: "#4f4741", chaud: "#5c4a3b", neon: "#161833", doux: .45 },
  plinthe: { tessera: "#2b221c", chaud: "#33231a", neon: "#0a0b1c", doux: .6 },
  sol: { tessera: "#4a3323", chaud: "#5a3b24", neon: "#0e0f1f", doux: .5 },
  "salle-mur": { tessera: "#2b3035", chaud: "#383230", neon: "#121430", doux: .45 },
};

/** Les choix de jour par défaut : Tessera, sauf ce que Benjamin a préféré en Chaud. */
const JOUR_PAR_DEFAUT = { machine: "chaud", tasse: "chaud" };

/** États : jamais thémés (ADR-026), mêmes teintes jour et nuit. */
const ETATS = { actif: "#60a5fa", attente: "#71717a", question: "#fbbf24", blocage: "#f87171", fait: "#4ade80" };

const MODES = {
  jour: { rim: null, outline: "selout" },
  nuit: { rim: "#5ef2ff", outline: "#07081a" },
};

/** Une base de famille pour un mode et des choix de jour. */
function baseDe(fam, mode, choix) {
  const f = FAMILLES[fam];
  if (!f) return "#ff00ff"; // famille inconnue : visible exprès
  if (mode === "nuit") return f.neon || f.tessera;
  const src = (choix && choix[fam]) || JOUR_PAR_DEFAUT[fam] || "tessera";
  return f[src] || f.tessera;
}

/**
 * Un résolveur jeton → couleur, mémoïsé. Syntaxe : « famille.ton », suivi de « ~r »
 * (liseré de lumière, la nuit) et/ou de « ^etat^n » (lueur d'un écran, palier 1 à 3, la nuit).
 */
function resolveur(mode, choix = {}) {
  const M = MODES[mode], cache = new Map(), rampes = new Map();
  const rampeDe = fam => {
    if (!rampes.has(fam)) rampes.set(fam, fam.startsWith("etat-") ? ramp(ETATS[fam.slice(5)]) : ramp(baseDe(fam, mode, choix), (FAMILLES[fam] && FAMILLES[fam].doux) || 1));
    return rampes.get(fam);
  };
  return tok => {
    if (cache.has(tok)) return cache.get(tok);
    let c;
    if (tok.startsWith("#")) c = tok;
    else {
      const [corps, etat, palier] = tok.split("^");
      const rim = corps.endsWith("~r"), [fam, ton] = corps.replace("~r", "").split(".");
      if (ton === "ol") c = M.outline === "selout" ? selout(rampeDe(fam).b) : M.outline;
      else c = rampeDe(fam)[ton] || "#ff00ff";
      if (rim && M.rim) c = mix(c, M.rim, .38);
      if (etat && mode === "nuit") c = mix(c, ramp(ETATS[etat]).hi, +palier * .16);
    }
    cache.set(tok, c);
    return c;
  };
}
