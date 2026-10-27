/**
 * Le gyrophare de la pièce, grille 10 × 8. Il ne se dessine que tant que la CI
 * est rouge (ADR-058) : le dôme clignote, le socle reste fixe. Sous
 * `prefers-reduced-motion` il reste allumé, sans clignoter.
 */
export default function Gyrophare() {
  return (
    <svg
      width="30"
      height="24"
      viewBox="0 0 10 8"
      shapeRendering="crispEdges"
      role="img"
      aria-label="CI rouge"
      data-sprite="gyrophare"
    >
      <g className="anim-gyro">
        <rect x="2" y="1" width="6" height="4" className="fill-(--sprite-gyrophare)" />
        <rect x="3" y="0" width="4" height="1" className="fill-(--sprite-gyrophare)" />
        <rect x="4" y="2" width="2" height="2" className="fill-(--sprite-gyrophare-clair)" />
      </g>
      <rect x="1" y="5" width="8" height="3" className="fill-(--sprite-gyrophare-socle)" />
    </svg>
  );
}
