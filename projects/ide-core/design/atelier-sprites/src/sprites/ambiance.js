"use strict";
/*
 * Ambiance : sol, mur, plinthe. Des tuiles qui se répètent : dans Tessera, une seule
 * image de fond par surface (un nœud), à la place des dégradés CSS d'aujourd'hui.
 * Échelle des tuiles : 1,75 px d'écran par pixel, comme le poste en grille ×2.
 */

/** Le parquet de la pièce de run, tuile 64 × 12 : longues lames décalées d'une demi-lame, fil du bois. */
function solParquet() {
  const s = mk(64, 12), g = s.L(), S = R("sol");
  for (let rang = 0; rang < 2; rang++) {
    const y = rang * 6, decal = rang ? 16 : 0;
    g.rect(0, y, 64, 5, S.b); g.rect(0, y, 64, 1, S.hi);
    for (let k = 0; k < 2; k++) {
      const x0 = (k * 32 + decal) % 64;
      if ((k + rang) % 2) for (let x = 1; x < 32; x++) g.rect((x0 + x) % 64, y + 1, 1, 4, S.hi);
      g.rect(x0, y, 1, 5, S.s);
      g.rect((x0 + 5 + rang * 7) % 64, y + 2, 7, 1, S.s); g.rect((x0 + 17 + rang * 3) % 64, y + 3, 5, 1, S.s);
    }
    g.rect(0, y + 5, 64, 1, S.d);
  }
  return s;
}
/** Le mur, tuile 32 × 32 : enduit à peine granuleux, quelques taches de lumière et d'ombre. */
function murEnduit(fam = "mur") {
  const s = mk(32, 32), g = s.L(), M = R(fam);
  g.rect(0, 0, 32, 32, M.b);
  // un tramage déterministe, clairsemé : le mur vibre sans dessiner de motif
  for (let i = 0; i < 32 * 32; i++) {
    let h = Math.imul(i ^ 0x9e3779b9, 0x85ebca6b); h ^= h >>> 13; h = Math.imul(h, 0xc2b2ae35); h ^= h >>> 16;
    const x = i % 32, y = Math.floor(i / 32), v = (h >>> 0) % 100;
    if (v < 3) g.set(x, y, M.hi); else if (v < 6) g.set(x, y, M.s);
  }
  return s;
}
/** La plinthe, tuile 16 × 6 : arête éclairée, corps, joint au sol. */
function plinthe() {
  const s = mk(16, 6), g = s.L(), B = R("plinthe");
  g.rect(0, 0, 16, 6, B.b); g.rect(0, 0, 16, 1, B.hi); g.rect(0, 5, 16, 1, B.d); g.rect(15, 1, 1, 4, B.s);
  return s;
}

function avantSol() { const s = mk(112, 21), g = s.L(); g.rect(0, 0, 112, 21, C.sol); g.rect(0, 11, 112, 1, "#211c18"); return s; }
function avantMur() { const s = mk(32, 32), g = s.L(); g.rect(0, 0, 32, 32, C.mur); return s; }
function avantPlinthe() { const s = mk(16, 6), g = s.L(); g.rect(0, 0, 16, 6, C.plinthe); return s; }

enregistrer({ id: "sol-parquet", nom: "Parquet de la pièce", fichier: "index.css (.sol-lames)", salle: "ambiance", grille: "rayures CSS → tuile 64 × 12", dw: 112, dh: 21,
  avant: avantSol, apres: solParquet, tuile: true,
  note: "Les rayures unies deviennent un parquet : lames décalées, quatre teintes, fil du bois. Une seule image de fond répétée, aucun nœud de plus." });
enregistrer({ id: "mur-enduit", nom: "Mur de la pièce", fichier: "FondDeLaPiece (bg-(--sprite-mur))", salle: "ambiance", grille: "uni → tuile 32 × 32", dw: 56, dh: 56,
  avant: avantMur, apres: murEnduit, tuile: true,
  note: "Un enduit à peine granuleux au lieu d'un aplat : le mur prend une matière sans attirer l'œil." });
enregistrer({ id: "plinthe", nom: "Plinthe", fichier: "FondDeLaPiece (border-b-4)", salle: "ambiance", grille: "bordure 4 px → tuile 16 × 6", dw: 28, dh: 10.5,
  avant: avantPlinthe, apres: plinthe, tuile: true,
  note: "Une arête éclairée et un joint au sol : la plinthe sépare enfin le mur du sol." });

/**
 * Une tuile en image de fond CSS : un seul nœud pour toute une surface. `s` est un
 * sprite déjà dessiné, `dw` × `dh` sa taille en px ; `cuire` dit s'il reçoit contour et liseré.
 */
function fondDeTuile(s, dw, dh, mode, choix, { cuire = false, repeat = "repeat" } = {}) {
  const b = bake(s, { outline: cuire, rim: cuire });
  const svg = toSvg(b, dw, dh, res(mode, choix), 'xmlns="http://www.w3.org/2000/svg"').html;
  return `url('data:image/svg+xml,${encodeURIComponent(svg)}') 0 0 / ${dw}px ${dh}px ${repeat}`;
}
