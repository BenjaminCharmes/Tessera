import type { EtatDuService } from "../../../design/etatDuService";
import { E, type Grille, R, type Sprite, cuire, delai, sprite } from "./grille";

/*
 * La salle des serveurs (atelier, `sprites/serveurs.js` et `salle-serveurs.js`,
 * ticket-727) : baies, climatiseur, bouche VMC, extincteur, porte coupe-feu. Seuls
 * les voyants portent un état (ADR-058), en jetons `etat-*` ; l'hélice rend une donnée.
 */

/** L'état d'un service → l'état qui teinte son voyant. « jamais-lancé » n'a pas de teinte à lui. */
export const ETAT_DU_VOYANT: Record<EtatDuService, string> = {
  "en-cours": "actif",
  echoue: "blocage",
  arrete: "attente",
  "jamais-lance": "attente",
};

/** La baie haute, 24 × 60 : sept serveurs 1U, un voyant ; en cours, une diode clignote par serveur. */
export function baieHaute(etat: EtatDuService): Sprite {
  const s = sprite(24, 60);
  const g = s.calque();
  const M = R("metal");
  const L = E(ETAT_DU_VOYANT[etat]);
  const activite = etat === "en-cours";
  g.rect(0, 0, 24, 60, M.d);
  g.rect(1, 1, 22, 58, M.b);
  g.rect(1, 1, 22, 1, M.hi);
  g.rect(1, 1, 1, 58, M.hi);
  g.rect(22, 2, 1, 57, M.s);
  g.rect(3, 3, 18, 6, M.d);
  g.rect(4, 4, 16, 4, "cadre.d");
  g.rect(5, 5, 7, 1, M.s);
  g.rect(5, 6, 4, 1, M.s);
  const v = s.calque();
  v.rect(16, 4, 4, 4, L.d);
  v.rect(17, 5, 2, 2, L.b);
  v.px(17, 5, L.hi);
  const diodes: number[] = [];
  for (let i = 0; i < 7; i++) {
    const y = 12 + i * 6;
    g.rect(3, y, 18, 5, M.s);
    g.rect(4, y + 1, 16, 3, M.b);
    g.rect(4, y + 1, 16, 1, M.hi);
    for (let x = 7; x < 15; x += 2) g.px(x, y + 2, M.d);
    g.rect(3, y + 1, 1, 3, M.hi);
    g.rect(20, y + 1, 1, 3, M.d);
    if (activite) diodes.push(y);
    else g.px(17, y + 2, M.d);
  }
  // Une diode par serveur, chacune à son rythme : le service tourne (une donnée, pas un décor).
  diodes.forEach((y, i) =>
    s
      .calque("anim-clignote", { ...delai(-((i * 0.37) % 1.1)), animationDuration: `${0.7 + (i % 3) * 0.35}s` })
      .px(17, y + 2, L.hi),
  );
  g.rect(2, 55, 20, 3, M.d);
  g.rect(3, 58, 3, 2, M.d);
  g.rect(18, 58, 3, 2, M.d);
  return cuire(s);
}

/** Le climatiseur, 32 × 44 : lames en relief, filtre à fentes, trappe de service. */
export function climatiseur(): Sprite {
  const s = sprite(32, 44);
  const g = s.calque();
  const M = R("metal");
  g.rect(0, 0, 32, 44, M.d);
  g.rect(1, 1, 30, 42, M.b);
  g.rect(1, 1, 30, 1, M.hi);
  g.rect(1, 1, 1, 42, M.hi);
  g.rect(30, 2, 1, 41, M.s);
  g.rect(2, 42, 29, 1, M.s);
  g.rect(3, 3, 26, 26, M.d);
  for (let y = 4; y < 28; y += 3) {
    g.rect(4, y, 24, 1, M.hi);
    g.rect(4, y + 1, 24, 1, M.s);
  }
  g.rect(3, 31, 26, 9, M.s);
  g.rect(4, 32, 24, 1, M.d);
  for (let x = 5; x < 27; x += 2) g.rect(x, 34, 1, 4, M.d);
  g.rect(24, 3, 4, 2, M.s);
  return cuire(s);
}

/** La petite baie de la pièce de run, 24 × (8 par étage + 4) : un serveur 2U par service. */
export function petiteBaie(etats: readonly EtatDuService[]): Sprite {
  const h = etats.length * 8 + 4;
  const s = sprite(24, h);
  const g = s.calque();
  const M = R("metal");
  g.rect(0, 0, 24, h, M.d);
  g.rect(1, 1, 22, h - 2, M.s);
  g.rect(1, 1, 22, 1, M.b);
  g.rect(1, 1, 1, h - 2, M.b);
  const v = s.calque();
  etats.forEach((e, i) => {
    const y = 2 + i * 8;
    const L = E(ETAT_DU_VOYANT[e]);
    g.rect(2, y, 20, 6, M.d);
    g.rect(3, y, 19, 5, M.b);
    g.rect(3, y, 19, 1, M.hi);
    g.rect(3, y, 1, 5, M.hi);
    g.rect(21, y + 1, 1, 4, M.s);
    g.rect(4, y + 1, 4, 4, "cadre.d");
    v.rect(5, y + 2, 2, 2, L.b);
    v.px(5, y + 2, L.hi);
    v.px(6, y + 3, L.s);
    for (let x = 9; x < 12; x += 1) for (let j = 1; j < 4; j += 2) g.px(x, y + j, M.d);
    for (const x of [13, 16, 19]) {
      g.rect(x, y + 1, 2, 3, M.s);
      g.px(x, y + 1, M.d);
      g.px(x + 1, y + 3, M.hi);
    }
  });
  g.rect(2, h - 2, 20, 1, M.d);
  return cuire(s);
}

/** Un disque plein d'un seul jeton. */
function rond(g: Grille, cx: number, cy: number, r: number, jeton: string): void {
  for (let y = Math.floor(cy - r); y <= cy + r; y++) {
    for (let x = Math.floor(cx - r); x <= cx + r; x++) {
      const dx = x + 0.5 - cx;
      const dy = y + 0.5 - cy;
      if (dx * dx + dy * dy <= r * r) g.set(x, y, jeton);
    }
  }
}

const PALE = [[14, 5, "s"], [15, 5, "b"], [16, 5, "b"], [13, 6, "hi"], [14, 6, "hi"], [15, 6, "b"], [16, 6, "b"], [17, 6, "s"],
  [13, 7, "hi"], [14, 7, "b"], [15, 7, "b"], [16, 7, "s"], [13, 8, "hi"], [14, 8, "b"], [15, 8, "s"],
  [13, 9, "hi"], [14, 9, "b"], [15, 9, "s"], [13, 10, "hi"], [14, 10, "s"], [13, 11, "hi"], [14, 11, "s"]] as const;

/** La bouche VMC, 28 × 28 : cadre vissé, carter rond, hélice à pales courbes, grille devant. `duree` : un quart de tour, absent à l'arrêt. */
export function boucheVmc(duree: string | null): Sprite {
  const s = sprite(28, 28);
  const g = s.calque();
  const M = R("metal");
  const D = R("dalle");
  g.rect(0, 0, 28, 28, M.d);
  g.rect(1, 1, 26, 26, M.b);
  g.rect(1, 1, 26, 1, M.hi);
  g.rect(1, 1, 1, 26, M.hi);
  g.rect(26, 2, 1, 25, M.s);
  g.rect(2, 26, 25, 1, M.s);
  for (const [x, y] of [[2, 2], [24, 2], [2, 24], [24, 24]] as const) {
    g.rect(x, y, 2, 2, M.s);
    g.px(x, y, M.hi);
  }
  g.rect(4, 4, 20, 20, D.d);
  rond(g, 14, 14, 10, M.s);
  rond(g, 14, 14, 9, D.d);
  // L'hélice : une pale, puis ses trois copies tournées d'un quart de tour autour de (14, 14).
  const hl = s.calque(duree ? "anim-helice" : "", duree ? { animationDuration: duree } : undefined);
  for (let q = 0; q < 4; q++) {
    for (const [x, y, t] of PALE) {
      let u = x + 0.5 - 14;
      let v = y + 0.5 - 14;
      for (let k = 0; k < q; k++) [u, v] = [-v, u];
      hl.set(Math.round(u + 14 - 0.5), Math.round(v + 14 - 0.5), `metal.${t}`);
    }
  }
  const m = s.calque();
  m.rect(12, 12, 4, 4, M.s);
  m.rect(13, 13, 2, 2, M.d);
  m.px(12, 12, M.hi);
  // La grille devant l'hélice, à 60 % : on voit l'hélice tourner derrière.
  const l = s.calque("", { opacity: "0.6" });
  for (const y of [6, 10, 14, 18, 22]) l.rect(4, y, 20, 1, M.s);
  return cuire(s);
}

/** L'extincteur, 12 × 28 : poignée, manomètre, corps arrondi, étiquette, tuyau le long du flanc. */
export function extincteur(): Sprite {
  const s = sprite(12, 28);
  const g = s.calque();
  const M = R("metal");
  const X = R("extincteur");
  const B = R("badge");
  const K = R("cadre");
  g.rect(2, 0, 6, 1, M.hi);
  g.rect(3, 1, 5, 1, M.b);
  g.px(7, 1, M.s);
  g.rect(8, 2, 4, 2, M.b);
  g.rect(8, 2, 4, 1, M.hi);
  g.rect(4, 2, 4, 4, M.b);
  g.rect(4, 2, 1, 4, M.hi);
  g.rect(7, 2, 1, 4, M.s);
  g.rect(3, 6, 6, 1, X.b);
  g.rect(2, 7, 8, 20, X.b);
  g.px(3, 6, X.hi);
  g.rect(3, 7, 1, 19, X.hi);
  g.rect(8, 7, 1, 20, X.s);
  g.rect(9, 7, 1, 20, X.d);
  g.rect(2, 26, 8, 1, X.d);
  g.rect(3, 27, 6, 1, K.d);
  g.rect(2, 14, 6, 6, B.b);
  g.rect(2, 14, 6, 1, B.hi);
  g.rect(3, 16, 4, 1, B.s);
  g.rect(3, 18, 3, 1, B.s);
  g.px(7, 19, B.d);
  g.rect(10, 4, 2, 18, K.b);
  g.rect(11, 4, 1, 18, K.s);
  g.rect(10, 21, 1, 2, K.b);
  g.px(10, 4, K.hi);
  return cuire(s);
}

/** La porte coupe-feu, 28 × 36 : hublot armé, ferme-porte, béquille, barre, lecteur de badge sans voyant. */
export function porteCoupeFeu(): Sprite {
  const s = sprite(28, 36);
  const g = s.calque();
  const M = R("metal");
  const K = R("cadre");
  const B = R("badge");
  g.rect(0, 0, 22, 36, M.d);
  g.rect(1, 1, 20, 35, M.s);
  g.rect(1, 1, 20, 1, M.b);
  g.rect(2, 2, 18, 34, M.b);
  g.rect(2, 2, 18, 1, M.hi);
  g.rect(2, 2, 1, 34, M.hi);
  g.rect(19, 3, 1, 33, M.s);
  for (const y of [6, 26]) {
    g.rect(1, y, 2, 3, M.d);
    g.px(2, y, M.s);
  }
  g.rect(10, 3, 8, 2, M.s);
  g.rect(10, 3, 8, 1, M.hi);
  g.px(17, 4, M.d);
  g.rect(4, 6, 14, 6, M.d);
  g.rect(5, 7, 12, 4, K.b);
  g.rect(5, 10, 12, 1, K.s);
  for (let x = 6; x < 17; x += 3) {
    g.px(x, 8, K.d);
    g.px(x + 1, 9, K.d);
  }
  g.line(7, 7, 10, 10, M.hi);
  g.line(8, 7, 11, 10, M.s);
  g.line(12, 7, 13, 8, M.s);
  g.rect(16, 17, 2, 4, M.s);
  g.rect(12, 18, 6, 1, M.hi);
  g.rect(12, 19, 6, 1, M.s);
  g.px(16, 17, M.hi);
  g.rect(4, 24, 14, 1, M.hi);
  g.rect(4, 25, 14, 1, M.d);
  g.rect(4, 24, 1, 2, M.s);
  g.rect(17, 24, 1, 2, M.s);
  g.rect(3, 31, 16, 4, M.s);
  g.rect(3, 31, 16, 1, M.hi);
  g.rect(18, 31, 1, 4, M.d);
  g.rect(22, 14, 6, 10, M.d);
  g.rect(23, 15, 4, 8, M.s);
  g.rect(23, 15, 4, 1, M.b);
  g.rect(23, 15, 1, 8, M.b);
  g.rect(24, 16, 2, 4, B.b);
  g.px(24, 16, B.hi);
  g.px(25, 19, B.s);
  g.px(24, 21, M.d);
  g.px(25, 21, M.d);
  return cuire(s);
}
