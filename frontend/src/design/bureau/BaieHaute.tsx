import type { EtatDuService } from "../etatDuService";
import { TON_VOYANT } from "./tons";

interface BaieHauteProps {
  /** L'état du service : son voyant le dit, seul élément de la baie qui porte un état. */
  etat: EtatDuService;
}

const GRILLE = [7, 10, 13, 16, 19, 22, 25];

/**
 * La baie haute de la salle des serveurs : une façade à grille d'aération et un
 * voyant, grille 12 × 30. Un service, une baie. Le corps est du mobilier fixe ;
 * seul le voyant rend un état (ADR-058).
 */
export default function BaieHaute({ etat }: BaieHauteProps) {
  return (
    <svg
      width="36"
      height="90"
      viewBox="0 0 12 30"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="baie-haute"
    >
      <rect x="0" y="0" width="12" height="30" className="fill-(--sprite-metal-ombre)" />
      <rect x="1" y="1" width="10" height="28" className="fill-(--sprite-metal)" />
      <rect x="2" y="2" width="8" height="3" className="fill-(--sprite-metal-ombre)" />
      <g data-voyant={etat}>
        <rect x="8" y="3" width="1" height="1" className={TON_VOYANT[etat]} />
      </g>
      {GRILLE.map((y) => (
        <rect key={y} x="2" y={y} width="8" height="1" className="fill-(--sprite-metal-ombre)" />
      ))}
      <rect x="9" y="27" width="1" height="1" className="fill-(--sprite-metal-clair)" />
    </svg>
  );
}
