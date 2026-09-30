/**
 * La bande d'en-tête d'une région — ticket-067.
 *
 * Chaque panneau avait choisi sa propre hauteur — `py-3` ici, `py-2` là,
 * `py-1.5` ailleurs — si bien qu'aucune barre supérieure ne s'alignait avec sa
 * voisine. Sur quatre colonnes côte à côte, le décalage se voit tout de suite,
 * même quand chaque panneau pris isolément paraît correct.
 *
 * Une seule hauteur pour toutes les bandes de premier niveau. Les bordures et
 * l'alignement horizontal restent au choix de chaque panneau : c'est la ligne
 * de base commune qui compte, pas l'uniformité du reste.
 */
export const BAND = "flex h-10 shrink-0 items-center";

/**
 * La grille du cockpit — ticket-252.
 *
 * Rail de navigation, colonne latérale, centre, et bandeau d'événements en
 * bas du centre. Les dimensions vivaient en `style` dans App.tsx : une grille
 * définie là où les autres constantes de mise en page le sont déjà.
 */
export const GRILLE_COCKPIT = {
  display: "grid",
  gridTemplateColumns: "100px 280px 1fr",
  gridTemplateRows: "1fr 180px",
} as const;
