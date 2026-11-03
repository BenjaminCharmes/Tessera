import { type Calque, type Sprite, tracer } from "./grille";
import { LISERE, liaisons, lueurGenerique, variableGenerique } from "./jeton";

/*
 * Les symboles partagés du Bureau (ticket-727). Dix pièces dessinent dix fois la
 * même chaise, le même bureau, la même bibliothèque : chaque calque devient un
 * `<symbol>` adressé par son contenu, posé une fois dans un `<defs>` commun, et
 * chaque instance n'est plus qu'un `<use>`. Deux calques de même dessin ont la
 * même empreinte, sans clé écrite à la main : rien ne peut partager à tort.
 */

/** Un chemin du symbole, la couleur déjà résolue en variable (générique ou non). */
export interface CheminDuSymbole {
  d: string;
  fill: string;
  opacity?: string;
}

/** Le contenu d'un symbole : sa grille et ses chemins, dans l'ordre de peinture. */
export interface ContenuDuSymbole {
  id: string;
  w: number;
  h: number;
  chemins: CheminDuSymbole[];
  /** Une tuile répétée (sol, mur) : un `<pattern>` à cette taille, déclaré sous son moment. */
  tuile?: { largeur: number; hauteur: number; moment: "jour" | "nuit" };
}

/** Une instance : le symbole qu'elle pose, sa classe d'animation et ses liaisons de couleur. */
export interface Instance {
  symbole: ContenuDuSymbole;
  classe: string;
  /** Les liaisons de couleur, et le décalage d'animation du calque. */
  style: Record<string, string>;
}

/** cyrb53 : une empreinte de 53 bits, sans dépendance, assez large pour quelques centaines de symboles. */
export function empreinte(texte: string): string {
  let h1 = 0xdeadbeef;
  let h2 = 0x41c6ce57;
  for (let i = 0; i < texte.length; i += 1) {
    const c = texte.charCodeAt(i);
    h1 = Math.imul(h1 ^ c, 2654435761);
    h2 = Math.imul(h2 ^ c, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return (4294967296 * (2097151 & h2) + (h1 >>> 0)).toString(36);
}

/** L'instance d'un calque, ou `null` s'il ne dessine rien. */
export function instanceDuCalque({ g, classe, style: propre }: Calque, w: number, h: number): Instance | null {
  const { fond, lisere, lueurs } = tracer(g);
  if (fond.length === 0) return null;
  const chemins: CheminDuSymbole[] = fond.map(({ jeton, d }) => ({ d, fill: variableGenerique(jeton) }));
  if (lisere) chemins.push({ d: lisere, ...LISERE });
  for (const { palier, d } of lueurs) chemins.push({ d, ...lueurGenerique(palier) });
  const familles = new Set(fond.map(({ jeton }) => jeton.split(".")[0] ?? ""));
  const id = `sp-${empreinte(`${w}x${h}|${chemins.map((c) => `${c.fill}${c.opacity ?? ""}:${c.d}`).join("|")}`)}`;
  const style = { ...liaisons(familles, lueurs[0]?.etat ?? null), ...propre };
  return { symbole: { id, w, h, chemins }, classe, style };
}

const instancesParSprite = new WeakMap<Sprite, Instance[]>();

/** Les instances d'un sprite, calque par calque, calculées une fois par objet sprite. */
export function instancesDuSprite(s: Sprite): Instance[] {
  let instances = instancesParSprite.get(s);
  if (!instances) {
    instances = s.calques.flatMap((c) => instanceDuCalque(c, s.w, s.h) ?? []);
    instancesParSprite.set(s, instances);
  }
  return instances;
}

/* ---------- Le registre : ce que le `<defs>` commun doit porter ---------- */

const inscrits = new Map<string, { contenu: ContenuDuSymbole; usages: number }>();
const abonnes = new Set<() => void>();
let instantane: readonly ContenuDuSymbole[] = [];

function publier(): void {
  instantane = [...inscrits.values()].map((e) => e.contenu);
  for (const f of abonnes) f();
}

/** Un usage de plus pour ce symbole ; le premier l'ajoute au `<defs>`. */
export function inscrire(contenu: ContenuDuSymbole): void {
  const e = inscrits.get(contenu.id);
  if (e) e.usages += 1;
  else {
    inscrits.set(contenu.id, { contenu, usages: 1 });
    publier();
  }
}

/** Un usage de moins ; le dernier retire le symbole du `<defs>`. */
export function liberer(id: string): void {
  const e = inscrits.get(id);
  if (!e) return;
  e.usages -= 1;
  if (e.usages <= 0) {
    inscrits.delete(id);
    publier();
  }
}

export function abonner(f: () => void): () => void {
  abonnes.add(f);
  return () => abonnes.delete(f);
}

/** Les symboles inscrits : la même référence tant que rien ne change. */
export function symbolesInscrits(): readonly ContenuDuSymbole[] {
  return instantane;
}

/**
 * Un dessin mémoïsé par ses arguments : le même objet sprite d'un rendu à l'autre,
 * donc les mêmes instances, sans recalcul toutes les dix secondes.
 */
export function memoise<A extends readonly (string | number | boolean)[], S extends Sprite | null>(
  dessin: (...a: A) => S,
): (...a: A) => S {
  const cache = new Map<string, S>();
  return (...a: A) => {
    const cle = a.join("|");
    if (!cache.has(cle)) cache.set(cle, dessin(...a));
    return cache.get(cle) as S;
  };
}
