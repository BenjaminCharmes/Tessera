import { TENUES, physique } from "../../lib/bureau/physique";
import Personnage from "./Personnage";

interface GoldFrameProps {
  /** Le projet dont le codeur pose : son physique est celui de son poste (ticket-595). */
  projet: string;
}

/**
 * Le cadre doré de l'employé de la semaine, grille 16 × 17 (32 × 34 px) : le buste
 * du codeur du projet sur un fond sourd. Il ne se dessine que si un projet a des
 * tickets approuvés au premier tour (ADR-058) ; le libellé est porté par l'objet
 * qui l'enveloppe.
 */
export default function GoldFrame({ projet }: GoldFrameProps) {
  return (
    <svg
      width="32"
      height="34"
      viewBox="0 0 16 17"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="cadre-employe"
    >
      <rect x="0" y="0" width="16" height="17" className="fill-(--sprite-cadre-dore)" />
      <rect x="1" y="1" width="14" height="15" className="fill-(--sprite-cadre-fond)" />
      {/* Le buste de la grille 16 × 18 du poste, descendu de trois unités dans le cadre. */}
      <g transform="translate(0 3)">
        <Personnage tenue={TENUES.codeur} physique={physique(projet, "codeur")} />
      </g>
    </svg>
  );
}
