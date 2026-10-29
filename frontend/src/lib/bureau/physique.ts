import type { RoleAffiche } from "./postesDuRun";

/** Indice d'un ton de peau (`--sprite-peau-N`) et d'une couleur de cheveux (`--sprite-cheveux-N`). */
export type Peau = 1 | 2 | 3 | 4 | 5;
export type Cheveux = 1 | 2 | 3 | 4 | 5 | 6;
export type Coiffure = "court" | "long" | "carre" | "chauve";

/** Ce qui change d'un agent à l'autre : tiré d'une graine stable, jamais de l'état du run. */
export interface Physique {
  peau: Peau;
  cheveux: Cheveux;
  coiffure: Coiffure;
  /** Jupe plutôt que pantalon : seulement avec des cheveux longs ou un carré. */
  jupe: boolean;
}

/** Ce qui change d'un rôle à l'autre : le jeu de couleurs du haut, et ses détails. */
export interface Tenue {
  /** Le jeu `--sprite-haut-<haut>` et `--sprite-haut-<haut>-ombre` (l'ombre colore les bras). */
  haut: RoleAffiche;
  capuche: boolean;
  cravate: boolean;
}

/**
 * La tenue de chaque rôle : sweat à capuche, blouse, veste, chemise à cravate, gilet.
 * L'architecte, qui prend le poste du codeur sur un ticket `design`, a la sienne : sans capuche.
 */
export const TENUES: Record<RoleAffiche, Tenue> = {
  codeur: { haut: "codeur", capuche: true, cravate: false },
  architect: { haut: "architect", capuche: false, cravate: false },
  testeur: { haut: "testeur", capuche: false, cravate: false },
  securite: { haut: "securite", capuche: false, cravate: false },
  reviewer: { haut: "reviewer", capuche: false, cravate: true },
  validateur: { haut: "validateur", capuche: false, cravate: false },
};

const PEAUX: readonly [Peau, ...Peau[]] = [1, 2, 3, 4, 5];
const CHEVEUX: readonly [Cheveux, ...Cheveux[]] = [1, 2, 3, 4, 5, 6];
const COIFFURES: readonly [Coiffure, ...Coiffure[]] = [
  "court",
  "long",
  "carre",
  "court",
  "chauve",
  "long",
];

/** Hachage de la maquette : petit, stable, sans dépendance. */
function graine(texte: string): number {
  let h = 7;
  for (let i = 0; i < texte.length; i += 1) h = (h * 31 + texte.charCodeAt(i)) % 100003;
  return h;
}

function choisir<T>(liste: readonly [T, ...T[]], i: number): T {
  return liste[i % liste.length] ?? liste[0];
}

/**
 * Le physique d'un agent : le même `projet` et le même `role` rendent toujours
 * le même résultat, d'un rendu et d'un run à l'autre.
 */
export function physique(projet: string, role: RoleAffiche): Physique {
  const g = graine(`${projet}:${role}`);
  const coiffure = choisir(COIFFURES, g);
  const cheveuxLongs = coiffure === "long" || coiffure === "carre";
  return {
    peau: choisir(PEAUX, g >> 2),
    cheveux: choisir(CHEVEUX, g >> 4),
    coiffure,
    jupe: cheveuxLongs && (g >> 6) % 2 === 0,
  };
}
