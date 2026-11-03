import type { ReactNode } from "react";
import { enPourcentDuSol } from "../../lib/bureau/etirementDuSol";

interface PoseProps {
  x: number;
  /** Où l'objet s'accroche : au sol par défaut, 4 px devant la plinthe ; sinon une classe de position (`top-9`, `bottom-10`). */
  bas?: string;
  /** L'abscisse est le centre de l'objet, pas son bord gauche. */
  centre?: boolean;
  /** Un décalage en pixels réels, ajouté à l'abscisse (la largeur d'un voisin agrandi). */
  decalage?: number;
  children: ReactNode;
}

/**
 * Un objet posé contre le mur, à une abscisse du repère de 800 px : au sol, devant la
 * plinthe et non sur elle (ticket-727), ou accroché à `bas`.
 */
export default function Pose({ x, bas = "-bottom-1", centre = false, decalage = 0, children }: PoseProps) {
  const left = decalage ? `calc(${enPourcentDuSol(x)} + ${decalage}px)` : enPourcentDuSol(x);
  return (
    <span className={`absolute ${bas}${centre ? " -translate-x-1/2" : ""}`} style={{ left }}>
      {children}
    </span>
  );
}
