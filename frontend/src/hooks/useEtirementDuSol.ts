import { createContext, useContext } from "react";

/** Le facteur d'étirement du sol de la pièce, posé par `SolEtire`. */
export const EtirementDuSol = createContext(1);

/** Le facteur qui étire les abscisses du repère de 800 px sur la largeur réelle du sol. */
export function useEtirementDuSol(): number {
  return useContext(EtirementDuSol);
}
