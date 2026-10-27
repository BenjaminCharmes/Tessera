/** Une chaise vue de face, grille 8 × 10 (24 × 30 px) : dossier, assise, pieds. Du mobilier fixe (ADR-058). */
export default function Chaise() {
  return (
    <svg
      width="24"
      height="30"
      viewBox="0 0 8 10"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="chaise"
    >
      <rect x="1" y="0" width="6" height="5" className="fill-(--sprite-table-ombre)" />
      <rect x="0" y="5" width="8" height="2" className="fill-(--sprite-table)" />
      <rect x="1" y="7" width="1" height="3" className="fill-(--sprite-table-ombre)" />
      <rect x="6" y="7" width="1" height="3" className="fill-(--sprite-table-ombre)" />
    </svg>
  );
}
