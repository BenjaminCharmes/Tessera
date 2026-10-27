import type { Physique, Tenue } from "../../lib/bureau/physique";
import Tete from "./Tete";
import { FILL_HAUT, FILL_OMBRE } from "./tons";

interface PersonnageAssisProps {
  tenue: Tenue;
  physique: Physique;
  tape: boolean;
}

/** Le personnage assis, dans la grille 16 × 18 du poste : buste, bras sur le clavier. */
export default function PersonnageAssis({ tenue, physique, tape }: PersonnageAssisProps) {
  const ombre = FILL_OMBRE[tenue.haut];
  return (
    <g data-sprite="personnage" data-pose="assis">
      <Tete physique={physique} x={5} y={3} />
      <rect x="4" y="7" width="8" height="5" className={FILL_HAUT[tenue.haut]} />
      {tenue.cravate && (
        <g data-detail="cravate">
          <rect x="7" y="7" width="2" height="1" className="fill-(--sprite-col)" />
          <rect x="7" y="8" width="2" height="3" className="fill-(--sprite-cravate)" />
        </g>
      )}
      {tenue.capuche && <rect data-detail="capuche" x="6" y="7" width="4" height="1" className={ombre} />}
      <g className={tape ? "anim-tape" : undefined}>
        <rect x="3" y="9" width="2" height="3" className={ombre} />
        <rect x="11" y="9" width="2" height="3" className={ombre} />
      </g>
    </g>
  );
}
