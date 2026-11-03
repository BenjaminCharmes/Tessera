import type { ReactNode } from "react";
import { enPourcentDuSol } from "../../lib/bureau/etirementDuSol";

interface PoseProps {
  x: number;
  /** Où l'objet s'accroche : au sol par défaut, 4 px devant la plinthe ; sinon une classe de position (`top-9`, `bottom-10`). */
  bas?: string;
  children: ReactNode;
}

/**
 * Un objet posé contre le mur, à une abscisse du repère de 800 px : au sol, devant la
 * plinthe et non sur elle (ticket-727), ou accroché à `bas`.
 */
export default function Pose({ x, bas = "-bottom-1", children }: PoseProps) {
  return (
    <span className={`absolute ${bas}`} style={{ left: enPourcentDuSol(x) }}>
      {children}
    </span>
  );
}
