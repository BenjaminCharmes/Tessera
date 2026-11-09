import { createContext, useContext, useSyncExternalStore } from "react";
import { echellePourLargeur } from "../lib/bureau/echelleDesSprites";

function abonner(rappel: () => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  window.addEventListener("resize", rappel);
  return () => window.removeEventListener("resize", rappel);
}

function lire(): number {
  return typeof window === "undefined" ? echellePourLargeur(Infinity) : echellePourLargeur(window.innerWidth);
}

/**
 * L'échelle commune des sprites du Bureau : la même dans les salles du haut et les
 * pièces des projets, réduite sur un écran étroit pour que les quatre salles tiennent
 * de front sans que leur mobilier se chevauche.
 */
export function useEchelleDesSprites(): number {
  const commune = useSyncExternalStore(abonner, lire, () => echellePourLargeur(Infinity));
  const imposee = useContext(EchelleImposee);
  return imposee ?? commune;
}

/** L'échelle qu'une pièce impose à ses sprites, à la place de l'échelle commune (ticket-898). */
const EchelleImposee = createContext<number | null>(null);

/** Impose une échelle à tous les sprites qu'il contient : la pièce d'un run a la sienne. */
export const FournisseurDEchelle = EchelleImposee.Provider;
