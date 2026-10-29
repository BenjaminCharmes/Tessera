import type { BoulesDeLaCorbeille } from "../../lib/bureau/corbeille";

interface CorbeilleProps {
  /** Une boule de papier froissé par refus du reviewer sur le ticket en cours, trois au plus. */
  boules: BoulesDeLaCorbeille;
}

/** Où se pose chaque boule : abscisse et ordonnée de sa case de 3 × 3 unités. */
const PLACES: readonly (readonly [x: number, y: number])[] = [
  [1, 1],
  [5, 1],
  [3, 0],
];

/**
 * La corbeille, grille 10 × 12 (20 × 24 px). Le seau est du mobilier, toujours là ;
 * chaque boule dit un fait du store de run : un refus du reviewer (ADR-058).
 */
export default function Corbeille({ boules }: CorbeilleProps) {
  return (
    <svg
      width="20"
      height="24"
      viewBox="0 0 10 12"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="corbeille"
      data-boules={boules}
    >
      {PLACES.slice(0, boules).map(([x, y]) => (
        <g key={`${x}-${y}`} data-detail="boule-de-papier">
          <rect x={x} y={y + 2} width="3" height="3" className="fill-(--sprite-papier)" />
          <rect x={x + 1} y={y + 1} width="2" height="1" className="fill-(--sprite-papier)" />
          <rect x={x + 2} y={y + 4} width="1" height="1" className="fill-(--sprite-papier-ombre)" />
        </g>
      ))}
      <rect x="0" y="5" width="10" height="1" className="fill-(--sprite-corbeille-ombre)" />
      <rect x="1" y="6" width="8" height="6" className="fill-(--sprite-corbeille)" />
      <rect x="3" y="7" width="1" height="4" className="fill-(--sprite-corbeille-ombre)" />
      <rect x="6" y="7" width="1" height="4" className="fill-(--sprite-corbeille-ombre)" />
    </svg>
  );
}
