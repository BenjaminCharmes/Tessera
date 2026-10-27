/** Un canapé, grille 24 × 10 (72 × 30 px) : dossier, assise, deux accoudoirs. Du mobilier fixe (ADR-058). */
export default function Canape() {
  return (
    <svg
      width="72"
      height="30"
      viewBox="0 0 24 10"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="canape"
    >
      <rect x="2" y="0" width="20" height="5" className="fill-(--sprite-canape)" />
      <rect x="0" y="3" width="3" height="6" className="fill-(--sprite-canape-ombre)" />
      <rect x="21" y="3" width="3" height="6" className="fill-(--sprite-canape-ombre)" />
      <rect x="3" y="5" width="18" height="3" className="fill-(--sprite-canape)" />
      <rect x="3" y="8" width="18" height="1" className="fill-(--sprite-canape-ombre)" />
      <rect x="1" y="9" width="1" height="1" className="fill-(--sprite-table-ombre)" />
      <rect x="22" y="9" width="1" height="1" className="fill-(--sprite-table-ombre)" />
    </svg>
  );
}
