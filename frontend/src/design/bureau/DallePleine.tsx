/**
 * Une dalle pleine du faux plancher, grille 12 × 12 : la voisine de
 * `DallePerforee`, à la même maille, pour que le sol se pose dalle par dalle.
 * Du mobilier : fixe, sans voyant (ADR-058).
 */
export default function DallePleine() {
  return (
    <svg
      width="36"
      height="36"
      viewBox="0 0 12 12"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="dalle-pleine"
    >
      <rect x="0" y="0" width="12" height="12" className="fill-(--sprite-dalle-joint)" />
      <rect x="1" y="1" width="10" height="10" className="fill-(--sprite-dalle)" />
    </svg>
  );
}
