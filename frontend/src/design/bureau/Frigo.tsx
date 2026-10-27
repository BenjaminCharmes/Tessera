/** Un réfrigérateur, grille 10 × 18 (30 × 54 px) : deux portes et leurs poignées. Du mobilier fixe (ADR-058). */
export default function Frigo() {
  return (
    <svg
      width="30"
      height="54"
      viewBox="0 0 10 18"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="frigo"
    >
      <rect x="0" y="0" width="10" height="18" className="fill-(--sprite-frigo-ombre)" />
      <rect x="1" y="1" width="8" height="5" className="fill-(--sprite-frigo)" />
      <rect x="1" y="7" width="8" height="10" className="fill-(--sprite-frigo)" />
      <rect x="7" y="3" width="1" height="2" className="fill-(--sprite-frigo-ombre)" />
      <rect x="7" y="8" width="1" height="3" className="fill-(--sprite-frigo-ombre)" />
    </svg>
  );
}
