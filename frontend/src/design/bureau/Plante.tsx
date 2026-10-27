/** Une plante en pot, posée dans un coin de pièce ou de salle : du mobilier fixe (ADR-058). Grille 8 × 10. */
export default function Plante() {
  return (
    <svg
      width="24"
      height="30"
      viewBox="0 0 8 10"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="plante"
    >
      <rect x="1" y="2" width="2" height="2" className="fill-(--sprite-plante)" />
      <rect x="5" y="1" width="2" height="3" className="fill-(--sprite-plante)" />
      <rect x="3" y="0" width="2" height="5" className="fill-(--sprite-plante-ombre)" />
      <rect x="2" y="4" width="4" height="1" className="fill-(--sprite-plante-ombre)" />
      <rect x="2" y="5" width="4" height="1" className="fill-(--sprite-pot)" />
      <rect x="2" y="6" width="4" height="4" className="fill-(--sprite-pot)" />
    </svg>
  );
}
