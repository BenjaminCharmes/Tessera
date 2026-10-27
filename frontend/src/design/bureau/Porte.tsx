/**
 * La porte au fond de la pièce, grille 12 × 18. Du mobilier : elle se dessine
 * toujours, fixe, sans voyant. C'est par elle que les agents partent à la fin
 * du run.
 */
export default function Porte() {
  return (
    <svg
      width="36"
      height="54"
      viewBox="0 0 12 18"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="porte"
    >
      <rect x="0" y="0" width="12" height="18" className="fill-(--sprite-porte-ombre)" />
      <rect x="1" y="1" width="10" height="17" className="fill-(--sprite-porte)" />
      <rect x="2" y="3" width="3" height="5" className="fill-(--sprite-porte-ombre)" />
      <rect x="7" y="3" width="3" height="5" className="fill-(--sprite-porte-ombre)" />
      <rect x="2" y="10" width="3" height="6" className="fill-(--sprite-porte-ombre)" />
      <rect x="7" y="10" width="3" height="6" className="fill-(--sprite-porte-ombre)" />
      <rect x="9" y="9" width="1" height="1" className="fill-(--sprite-tasse)" />
    </svg>
  );
}
