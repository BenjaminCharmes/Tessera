import type { EcranId } from "../ecranDuPoste";
import { E, type Grille, R, type Sprite, cuire, sprite } from "./grille";

/*
 * Les scènes de l'écran d'un poste, 12 × 8 (atelier, `sprites/salle-serveurs.js`,
 * ticket-727). Leurs traits ne portent que des tons d'état (ADR-026). Une animation
 * n'est posée que si l'agent travaille réellement : immobile, la scène dit « rien ne
 * bouge », elle ne ment pas (ADR-058).
 */

/**
 * Une animation image par image : n calques, un seul visible à la fois. Le premier
 * reste visible sans CSS ; les autres sont masqués, l'animation les dévoile tour à tour.
 */
function trame(s: ReturnType<typeof sprite>, n: 6 | 8, duree: number, dessin: (g: Grille, i: number) => void): void {
  for (let i = 0; i < n; i++) {
    const style: Record<string, string> = {
      animationDuration: `${duree}s`,
      animationDelay: `-${+((i * duree) / n).toFixed(3)}s`,
    };
    if (i) style.opacity = "0";
    dessin(s.calque(`anim-trame anim-trame-${n}`, style), i);
  }
}

/** Lignes de code indentées : un motif de huit lignes qui boucle sans saut. */
const CODE = [[0, 0, 2, "hi"], [3, 0, 4, "b"], [2, 2, 6, "b"], [2, 4, 3, "s"], [6, 4, 3, "b"], [0, 6, 4, "b"]] as const;

/** La scène d'un écran dans le ton de l'état (`actif`, `question`…), ou `null` sans scène. */
export function scene(ecran: EcranId, ton: string, anime: boolean): Sprite | null {
  const s = sprite(12, 8);
  // Le fond éteint, sous la scène : sans lui, le contour comblerait les interlignes.
  s.calque().rect(0, 0, 12, 8, "ecran-fond.b");
  const L = E(ton);
  const A = E("attente");
  const Pg = R("ecran-page");
  switch (ecran) {
    case "code": {
      const motif = (g: Grille, k: number) => {
        for (const [x, y, w, t] of CODE) g.rect(x, (y - k + 8) % 8, w, 1, L[t]);
      };
      if (anime) trame(s, 8, 1.2, motif);
      else motif(s.calque(), 0);
      break;
    }
    case "lecture": {
      const g = s.calque();
      g.rect(2, 0, 8, 8, Pg.b);
      g.rect(9, 1, 1, 7, Pg.s);
      g.clr(9, 0);
      g.px(8, 0, Pg.hi);
      g.px(8, 1, Pg.s);
      for (const [y, w] of [[2, 5], [4, 4], [6, 5]] as const) g.rect(3, y, w, 1, Pg.d);
      break;
    }
    case "tests": {
      s.calque().rect(0, 2, 12, 4, A.d);
      const barre = (b: Grille, w: number) => {
        b.rect(0, 2, w, 4, L.b);
        b.rect(0, 2, w, 1, L.hi);
        b.rect(0, 5, w, 1, L.s);
      };
      if (anime) trame(s, 6, 1.8, (b, i) => barre(b, 2 + i * 2));
      else barre(s.calque(), 6);
      break;
    }
    case "audit": {
      const g = s.calque();
      for (const [x, y, w] of [[0, 0, 10], [0, 2, 12], [2, 4, 7], [0, 6, 11]] as const) g.rect(x, y, w, 1, A.d);
      const ligne = (b: Grille, y: number) => {
        b.rect(0, y, 12, 1, L.hi);
        b.rect(0, y + 1, 12, 1, L.b);
      };
      if (anime) trame(s, 8, 1.2, ligne);
      else ligne(s.calque(), 2);
      break;
    }
    case "diff": {
      const g = s.calque(anime ? "anim-lueur" : "");
      const V = E("fait");
      const Ro = E("blocage");
      ([[V, 8], [Ro, 6], [V, 10], [Ro, 4]] as const).forEach(([T, w], i) => {
        g.px(0, i * 2, T.hi);
        g.rect(2, i * 2, w, 1, T.b);
      });
      break;
    }
    case "criteres": {
      const g = s.calque(anime ? "anim-lueur" : "");
      for (const [y, w] of [[0, 7], [3, 9], [6, 5]] as const) {
        g.rect(0, y, 2, 2, Pg.b);
        g.px(1, y + 1, Pg.s);
        g.rect(3, y, w, 1, L.b);
      }
      break;
    }
    case "ok": {
      const g = s.calque();
      const V = E("fait");
      g.line(1, 4, 3, 6, V.s);
      g.line(3, 6, 9, 0, V.s);
      g.line(1, 3, 3, 5, V.b);
      g.line(3, 5, 8, 0, V.b);
      g.px(8, 0, V.hi);
      g.px(1, 3, V.hi);
      break;
    }
    case "ko": {
      const g = s.calque();
      const Ro = E("blocage");
      g.line(3, 0, 10, 7, Ro.s);
      g.line(10, 0, 3, 7, Ro.s);
      g.line(2, 0, 9, 7, Ro.b);
      g.line(9, 0, 2, 7, Ro.b);
      g.px(2, 0, Ro.hi);
      break;
    }
    default:
      return null;
  }
  return cuire(s);
}
