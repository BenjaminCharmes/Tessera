import { useSyncExternalStore } from "react";

/** L'échelle des sprites sur un grand écran, et sur un écran étroit (portable, zoom du navigateur). */
export const ECHELLE_LARGE = 1.5;
export const ECHELLE_ETROITE = 1.25;
const ECRAN_ETROIT = "(max-width: 1599px)";

function requete(): MediaQueryList | null {
  return typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? window.matchMedia(ECRAN_ETROIT)
    : null;
}

function abonner(rappel: () => void): () => void {
  const mq = requete();
  mq?.addEventListener("change", rappel);
  return () => mq?.removeEventListener("change", rappel);
}

function lire(): number {
  return requete()?.matches ? ECHELLE_ETROITE : ECHELLE_LARGE;
}

/**
 * L'échelle commune des sprites du Bureau : la même dans les salles du haut et les
 * pièces des projets, plus petite sur un écran étroit pour que rien ne se chevauche.
 */
export function useEchelleDesSprites(): number {
  return useSyncExternalStore(abonner, lire, () => ECHELLE_LARGE);
}
