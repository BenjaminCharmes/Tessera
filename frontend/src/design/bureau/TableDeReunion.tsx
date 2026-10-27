/**
 * La table de la salle de réunion, grille 24 × 12. Du mobilier : ni personnage
 * ni feuille, ce que la salle occupée montre vient des occupants.
 */
export default function TableDeReunion() {
  return (
    <svg
      width="72"
      height="36"
      viewBox="0 0 24 12"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="table-de-reunion"
    >
      <rect x="2" y="2" width="20" height="5" className="fill-(--sprite-table)" />
      <rect x="2" y="7" width="20" height="1" className="fill-(--sprite-table-ombre)" />
      <rect x="4" y="8" width="2" height="4" className="fill-(--sprite-table-ombre)" />
      <rect x="18" y="8" width="2" height="4" className="fill-(--sprite-table-ombre)" />
      <rect x="0" y="3" width="1" height="3" className="fill-(--sprite-machine-ombre)" />
      <rect x="23" y="3" width="1" height="3" className="fill-(--sprite-machine-ombre)" />
    </svg>
  );
}
