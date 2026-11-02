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

/** La lueur d'un écran, palier 1 à 3 : la teinte claire de l'état, plus forte près de l'écran. */
export function lueur(etat: string, palier: number): { fill: string; opacity: string } {
  return {
    fill: `var(--sprite-etat-${etat}-hi)`,
    opacity: `calc(var(--sprite-lueur-force) * ${(palier * 0.16).toFixed(2)})`,
  };
}
