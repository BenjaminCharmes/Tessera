import type { ReactNode } from "react";
import { useEchelleDesSprites } from "../../hooks/useEchelleDesSprites";

interface AgrandiProps {
  /** Un multiple de l'échelle commune, pour un objet qui doit dominer le mur (le tableau blanc). */
  relatif?: number;
  children: ReactNode;
}

/**
 * Agrandit un sprite en pixel art à l'échelle commune du Bureau (`useEchelleDesSprites`) :
 * `zoom` change aussi la place prise dans le flux, les voisins s'écartent. Les sprites
 * gardent `crispEdges`, ils restent nets.
 */
export default function Agrandi({ relatif = 1, children }: AgrandiProps) {
  const facteur = useEchelleDesSprites() * relatif;
  return (
    <span className="inline-block align-bottom" style={{ zoom: facteur }} data-agrandi={facteur}>
      {children}
    </span>
  );
}
