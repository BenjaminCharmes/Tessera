"use strict";
/*
 * Ambiance : sol, mur, plinthe. Des tuiles qui se répètent : dans Tessera, une seule
 * image de fond par surface (un nœud), à la place des dégradés CSS d'aujourd'hui.
 * Échelle des tuiles : 1,75 px d'écran par pixel, comme le poste en grille ×2.
 */

/** Le parquet de la pièce de run, tuile 32 × 12 : lames décalées, teintes variées, fil du bois. */
function solParquet() {
  const s = mk(32, 12), g = s.L(), S = R("sol");
  const tons = [S.b, S.hi, S.b, S.hi];
  for (let rang = 0; rang < 2; rang++) {
    const y = rang * 6, decal = rang ? 8 : 0;
    for (let k = 0; k < 3; k++) {
      const x0 = -decal + k * 16, ton = tons[(k + rang * 2) % 4];
      for (let x = x0; x < x0 + 16; x++) {
        const xx = ((x % 32) + 32) % 32;
        g.rect(xx, y, 1, 5, ton);
        g.set(xx, y, S.hi);
      }
      const xj = ((x0 % 32) + 32) % 32;
      g.rect(xj, y, 1, 5, S.s);
      // le fil du bois : deux traits courts par lame
      const xg = ((x0 + 4 + rang * 3) % 32 + 32) % 32;
      g.rect(xg, y + 2, 4, 1, S.s); g.rect((xg + 7) % 32, y + 3, 3, 1, S.s);
    }
    g.rect(0, y + 5, 32, 1, S.s);
  }
  return s;
}
/** Le mur, tuile 32 × 32 : enduit à peine granuleux, quelques taches de lumière et d'ombre. */
function murEnduit() {
  const s = mk(32, 32), g = s.L(), M = R("mur");
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

function avantSol() { const s = mk(56, 21), g = s.L(); g.rect(0, 0, 56, 21, C.sol); g.rect(0, 11, 56, 1, "#211c18"); return s; }
function avantMur() { const s = mk(32, 32), g = s.L(); g.rect(0, 0, 32, 32, C.mur); return s; }
function avantPlinthe() { const s = mk(16, 6), g = s.L(); g.rect(0, 0, 16, 6, C.plinthe); return s; }

enregistrer({ id: "sol-parquet", nom: "Parquet de la pièce", fichier: "index.css (.sol-lames)", salle: "ambiance", grille: "rayures CSS → tuile 32 × 12", dw: 56, dh: 21,
  avant: avantSol, apres: solParquet, tuile: true,
  note: "Les rayures unies deviennent un parquet : lames décalées, quatre teintes, fil du bois. Une seule image de fond répétée, aucun nœud de plus." });
enregistrer({ id: "mur-enduit", nom: "Mur de la pièce", fichier: "FondDeLaPiece (bg-(--sprite-mur))", salle: "ambiance", grille: "uni → tuile 32 × 32", dw: 56, dh: 56,
  avant: avantMur, apres: murEnduit, tuile: true,
  note: "Un enduit à peine granuleux au lieu d'un aplat : le mur prend une matière sans attirer l'œil." });
enregistrer({ id: "plinthe", nom: "Plinthe", fichier: "FondDeLaPiece (border-b-4)", salle: "ambiance", grille: "bordure 4 px → tuile 16 × 6", dw: 28, dh: 10.5,
  avant: avantPlinthe, apres: plinthe, tuile: true,
  note: "Une arête éclairée et un joint au sol : la plinthe sépare enfin le mur du sol." });

/** Une tuile en image de fond CSS : un seul nœud pour toute une surface. */
function fondDeTuile(def, mode, choix, echelle = 1) {
  const s = bake(def.apres(), { outline: false, rim: false });
  const svg = toSvg(s, def.dw * echelle, def.dh * echelle, res(mode, choix), 'xmlns="http://www.w3.org/2000/svg"').html;
  return `url("data:image/svg+xml,${encodeURIComponent(svg)}") 0 0 / ${def.dw * echelle}px ${def.dh * echelle}px repeat`;
}
