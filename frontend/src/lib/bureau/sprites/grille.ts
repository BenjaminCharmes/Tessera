/*
 * Le moteur des sprites du Bureau, porté de l'atelier (ticket-727). Un sprite est
 * une pile de calques ; chaque pixel porte un JETON, jamais une couleur :
 * « famille.ton » (plante.b, metal.hi…) ou « etat-actif.hi » pour un voyant.
 * Les tons : hi (reflet), b (base), s (ombre), d (creux), bl (joue), ol (contour).
 * La couleur se résout en CSS (`jeton.ts`) : le jour et la nuit ne changent que
 * des variables.
 */

/** Un jeton de pixel, éventuellement marqué « ~r » (liseré) ou « ^etat^palier » (lueur). */
export type Jeton = string;

/** Une grille de jetons, w × h, `null` pour un pixel vide. */
export class Grille {
  readonly w: number;
  readonly h: number;
  readonly p: (Jeton | null)[];

  constructor(w: number, h: number) {
    this.w = w;
    this.h = h;
    this.p = new Array<Jeton | null>(w * h).fill(null);
  }

  set(x: number, y: number, c: Jeton): void {
    if (x >= 0 && y >= 0 && x < this.w && y < this.h) this.p[y * this.w + x] = c;
  }

  get(x: number, y: number): Jeton | null {
    return x < 0 || y < 0 || x >= this.w || y >= this.h ? null : (this.p[y * this.w + x] ?? null);
  }

  rect(x: number, y: number, w: number, h: number, c: Jeton): void {
    for (let j = y; j < y + h; j++) for (let i = x; i < x + w; i++) this.set(i, j, c);
  }

  px(x: number, y: number, c: Jeton): void {
    this.set(x, y, c);
  }

  clr(x: number, y: number): void {
    if (x >= 0 && y >= 0 && x < this.w && y < this.h) this.p[y * this.w + x] = null;
  }

  /** Une ligne de pixels de (x0, y0) à (x1, y1), tracée à la Bresenham. */
  line(x0: number, y0: number, x1: number, y1: number, c: Jeton): void {
    const dx = Math.abs(x1 - x0);
    const dy = -Math.abs(y1 - y0);
    const sx = x0 < x1 ? 1 : -1;
    const sy = y0 < y1 ? 1 : -1;
    let e = dx + dy;
    for (;;) {
      this.set(x0, y0, c);
      if (x0 === x1 && y0 === y1) break;
      const e2 = 2 * e;
      if (e2 >= dy) {
        e += dy;
        x0 += sx;
      }
      if (e2 <= dx) {
        e += dx;
        y0 += sy;
      }
    }
  }

  /** Un disque plein, ombré par sa position : reflet en haut à gauche, ombre en bas à droite. */
  disc(cx: number, cy: number, r: number, fam: string, { ombre = true } = {}): void {
    for (let y = Math.floor(cy - r); y <= cy + r; y++) {
      for (let x = Math.floor(cx - r); x <= cx + r; x++) {
        const dx = x - cx;
        const dy = y - cy;
        const d2 = dx * dx + dy * dy;
        if (d2 > r * r + 0.6) continue;
        if (!ombre) {
          this.set(x, y, `${fam}.b`);
          continue;
        }
        const t = (dx + dy) / r;
        let ton = t < -0.75 ? "hi" : t < 0.35 ? "b" : "s";
        if (d2 > (r - 1) * (r - 1) + 0.6 && t > 0.3) ton = "d";
        this.set(x, y, `${fam}.${ton}`);
      }
    }
  }

  /** Un motif texte : chaque caractère renvoie à un jeton par `table`, « . » est vide. */
  stamp(x: number, y: number, lignes: readonly string[], table: Readonly<Record<string, Jeton>>): void {
    lignes.forEach((ligne, j) =>
      [...ligne].forEach((ch, i) => {
        const c = table[ch];
        if (c !== undefined) this.set(x + i, y + j, c);
      }),
    );
  }
}

/** Un calque : sa grille, la classe d'animation et le style (décalage, durée, opacité) que porte son `<use>`. */
export interface Calque {
  g: Grille;
  classe: string;
  style?: Readonly<Record<string, string>>;
}

export interface Sprite {
  w: number;
  h: number;
  calques: Calque[];
}

/** Un sprite vide ; `calque()` lui ajoute un calque au-dessus des autres. */
export function sprite(
  w: number,
  h: number,
): Sprite & { calque: (classe?: string, style?: Readonly<Record<string, string>>) => Grille } {
  const s: Sprite = { w, h, calques: [] };
  return {
    ...s,
    calques: s.calques,
    calque(classe = "", style?: Readonly<Record<string, string>>) {
      const g = new Grille(w, h);
      s.calques.push(style === undefined ? { g, classe } : { g, classe, style });
      return g;
    },
  };
}

/** Le décalage d'une animation, en secondes (négatif : déjà en cours). */
export const delai = (secondes: number) => ({ animationDelay: `${secondes}s` });

/**
 * Le style de l'image `i` sur `n` d'une animation image par image de `duree` secondes.
 * La keyframe montre l'image sur le premier 1/n du cycle : l'image `i` doit s'y trouver
 * à l'instant `i·duree/n`, donc avancée de `(n − i)·duree/n`. Avec `i·duree/n`, les images
 * passaient à l'envers (0, n−1, …, 1). Hors de l'animation, seule la première se voit.
 */
export function imageParImage(i: number, n: number, duree: number): Record<string, string> {
  const avance = (((n - i) % n) * duree) / n;
  const style: Record<string, string> = {
    animationDuration: `${duree}s`,
    animationDelay: `${avance ? "-" : ""}${+avance.toFixed(3)}s`,
  };
  if (i) style.opacity = "0";
  return style;
}

/** Les cinq tons d'une famille, sous la forme qu'attendent les fonctions de dessin. */
export const R = (fam: string) => ({ hi: `${fam}.hi`, b: `${fam}.b`, s: `${fam}.s`, d: `${fam}.d`, bl: `${fam}.bl` });
/** Les tons d'un état : voyants, écrans, cases. Jamais thémés, jamais contourés (ADR-026). */
export const E = (etat: string) => R(`etat-${etat}`);

const occupe = (s: Sprite, x: number, y: number): boolean => s.calques.some(({ g }) => g.get(x, y) !== null);
const famille = (t: Jeton): string => t.split(".")[0] ?? t;

/**
 * La cuisson : liseré de lumière (« ~r ») sur les bords exposés en haut et à gauche,
 * puis contour sélectif (« famille.ol ») autour de la silhouette. Un jeton `etat-*`
 * n'en reçoit pas : un voyant garde sa teinte (ADR-026).
 */
export function cuire(s: Sprite, { contour = true, lisere = true } = {}): Sprite {
  if (lisere) {
    for (const { g } of s.calques) {
      const src = g.p.slice();
      for (let y = 0; y < s.h; y++) {
        for (let x = 0; x < s.w; x++) {
          const c = src[y * s.w + x];
          if (!c || c.startsWith("etat") || c.endsWith(".ol")) continue;
          if (!occupe(s, x - 1, y) || !occupe(s, x, y - 1)) g.set(x, y, `${c}~r`);
        }
      }
    }
  }
  if (contour) {
    for (const { g } of s.calques) {
      const src = g.p.slice();
      const en = (x: number, y: number) => (x < 0 || y < 0 || x >= s.w || y >= s.h ? null : src[y * s.w + x]);
      for (let y = 0; y < s.h; y++) {
        for (let x = 0; x < s.w; x++) {
          if (occupe(s, x, y)) continue;
          const voisin = en(x - 1, y) ?? en(x + 1, y) ?? en(x, y - 1) ?? en(x, y + 1);
          if (!voisin) continue;
          const f = famille(voisin.replace("~r", ""));
          if (!f.startsWith("etat")) g.set(x, y, `${f}.ol`);
        }
      }
    }
  }
  return s;
}

/** Un chemin SVG : le coût réel dans le DOM. */
export interface Trace {
  jeton: Jeton;
  d: string;
}

/** Une lueur d'écran : les pixels d'un palier, à recouvrir de la teinte de l'état. */
export interface Lueur {
  etat: string;
  palier: number;
  d: string;
}

/**
 * Ce qu'un calque dessine. Le liseré et la lueur ne multiplient pas les jetons : mêler
 * une couleur à t % revient à poser la teinte ajoutée par-dessus, à l'opacité t. Un
 * chemin de liseré et un par palier de lueur, au lieu d'un par jeton marqué.
 */
export interface TracesDuCalque {
  fond: Trace[];
  lisere: string | null;
  lueurs: Lueur[];
}

/** Ajoute à `d` la bande [x, e) de la ligne y. */
const bande = (d: string | undefined, x: number, e: number, y: number) => `${d ?? ""}M${x} ${y}h${e - x}v1h${x - e}z`;

/** Parcourt une grille en bandes horizontales de même clé ; une clé vide est sautée. */
function bandes(g: Grille, cle: (c: Jeton) => string | null): Map<string, string> {
  const parCle = new Map<string, string>();
  for (let y = 0; y < g.h; y++) {
    let x = 0;
    while (x < g.w) {
      const c = g.p[y * g.w + x];
      const k = c ? cle(c) : null;
      let e = x + 1;
      while (e < g.w && g.p[y * g.w + e] && cle(g.p[y * g.w + e] as Jeton) === k) e++;
      if (k !== null) parCle.set(k, bande(parCle.get(k), x, e, y));
      x = e;
    }
  }
  return parCle;
}

/** Les traces d'un calque : le fond par jeton nu, puis le liseré, puis les lueurs. */
export function tracer(g: Grille): TracesDuCalque {
  const nu = (c: Jeton) => (c.split("^")[0] ?? c).replace("~r", "");
  const fond = [...bandes(g, nu)].map(([jeton, d]) => ({ jeton, d }));
  const lisere = bandes(g, (c) => (c.includes("~r") ? "r" : null)).get("r") ?? null;
  const lueurs = [...bandes(g, (c) => (c.includes("^") ? c.slice(c.indexOf("^") + 1) : null))].map(([k, d]) => {
    const [etat = "", palier = "0"] = k.split("^");
    return { etat, palier: Number(palier), d };
  });
  return { fond, lisere, lueurs };
}
