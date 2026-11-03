/*
 * Un jeton → sa variable CSS (ticket-727). La couleur vit dans les variables
 * `--sprite-<famille>-<ton>` (`sprites-theme.css`, générées par l'atelier) ; la
 * nuit les redéfinit sous `[data-moment="nuit"]`, avec la force du liseré et de la
 * lueur des écrans, nulle le jour.
 */

/** La variable d'un jeton nu : « peau2.b » → `var(--sprite-peau2-b)`. */
export function variable(jeton: string): string {
  const [fam, ton] = jeton.split(".");
  return `var(--sprite-${fam}-${ton})`;
}

/** Le liseré de lumière : sa teinte, à l'opacité que le moment lui donne. */
export const LISERE = { fill: "var(--sprite-lisere)", opacity: "var(--sprite-lisere-force)" };

/** L'opacité d'un palier de lueur (1 à 3) : plus forte près de l'écran, nulle le jour. */
const forceDuPalier = (palier: number) => `calc(var(--sprite-lueur-force) * ${(palier * 0.16).toFixed(2)})`;

/** La lueur d'un écran, palier 1 à 3 : la teinte claire de l'état, plus forte près de l'écran. */
export function lueur(etat: string, palier: number): { fill: string; opacity: string } {
  return { fill: `var(--sprite-etat-${etat}-hi)`, opacity: forceDuPalier(palier) };
}

/*
 * Les familles qui changent d'un agent à l'autre (peau, cheveux, haut du rôle) ne
 * changent pas sa géométrie. Un symbole partagé les lit dans une variable
 * générique (`--sp-peau-b`), que le `<use>` lie à la vraie (`--sprite-peau3-b`) :
 * deux agents de même coiffure et de même expression partagent leur dessin.
 */
const GENERIQUES: readonly [RegExp, string][] = [
  [/^peau\d+$/, "peau"],
  [/^cheveux\d+$/, "cheveux"],
  [/^haut-[a-z-]+$/, "haut"],
];

/** La famille générique d'une famille, ou `null` si elle ne varie pas d'un agent à l'autre. */
export function generique(famille: string): string | null {
  for (const [motif, nom] of GENERIQUES) if (motif.test(famille)) return nom;
  return null;
}

/** La variable d'un jeton dans un symbole partagé : générique si sa famille l'est. */
export function variableGenerique(jeton: string): string {
  const [fam = "", ton] = jeton.split(".");
  const g = generique(fam);
  return g ? `var(--sp-${g}-${ton})` : variable(jeton);
}

/** La lueur dans un symbole partagé : la teinte de l'état vient du `<use>` (`--sp-lueur`). */
export function lueurGenerique(palier: number): { fill: string; opacity: string } {
  return { fill: "var(--sp-lueur)", opacity: forceDuPalier(palier) };
}

const TONS = ["hi", "b", "s", "d", "bl", "ol"] as const;

/**
 * Les liaisons qu'un `<use>` pose pour son symbole : chaque famille générique
 * rencontrée vers sa vraie famille, tous tons ; la lueur vers la teinte de l'état.
 */
export function liaisons(familles: Iterable<string>, etatDeLueur: string | null): Record<string, string> {
  const style: Record<string, string> = {};
  for (const fam of familles) {
    const g = generique(fam);
    if (g) for (const ton of TONS) style[`--sp-${g}-${ton}`] = `var(--sprite-${fam}-${ton})`;
  }
  if (etatDeLueur) style["--sp-lueur"] = `var(--sprite-etat-${etatDeLueur}-hi)`;
  return style;
}
