import { createContext, useContext } from "react";

/** Le facteur d'étirement du sol de la pièce, posé par `SolEtire`. */
export const EtirementDuSol = createContext(1);

/**
 * Vrai une fois le sol mesuré et peint : avant, un agent qui change de place ne marche
 * pas. Lire la largeur au montage calculait le style des agents à l'étirement 1, et le
 * vrai étirement les faisait glisser depuis la gauche à chaque retour sur la vue
 * (ticket-638). Vrai par défaut : hors d'un `SolEtire`, rien ne se mesure.
 */
export const MarcheActive = createContext(true);

export function useMarcheActive(): boolean {
  return useContext(MarcheActive);
}

/** Le facteur qui étire les abscisses du repère de 800 px sur la largeur réelle du sol. */
export function useEtirementDuSol(): number {
  return useContext(EtirementDuSol);
}
