const TROUS = [3, 5, 7, 9];

/**
 * Une dalle perforée du faux plancher, grille 12 × 12 : à la même maille que
 * les dalles pleines du sol. Du mobilier : fixe, sans voyant.
 */
export default function DallePerforee() {
  return (
    <svg
      width="36"
      height="36"
      viewBox="0 0 12 12"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="dalle-perforee"
    >
      <rect x="0" y="0" width="12" height="12" className="fill-(--sprite-dalle-joint)" />
      <rect x="1" y="1" width="10" height="10" className="fill-(--sprite-dalle)" />
      {TROUS.flatMap((y) =>
        TROUS.map((x) => (
          <rect key={`${x}-${y}`} x={x} y={y} width="1" height="1" className="fill-(--sprite-dalle-trou)" />
        )),
      )}
    </svg>
  );
}
