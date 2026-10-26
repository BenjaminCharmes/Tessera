/** Un dossier de la pile : un ticket de la file qui n'a pas encore été traité. Grille 10 × 8. */
export default function Dossier() {
  return (
    <svg
      width="30"
      height="24"
      viewBox="0 0 10 8"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="dossier"
    >
      <rect x="0" y="0" width="4" height="2" className="fill-(--sprite-dossier-ombre)" />
      <rect x="0" y="1" width="10" height="7" className="fill-(--sprite-dossier)" />
      <rect x="0" y="7" width="10" height="1" className="fill-(--sprite-dossier-ombre)" />
    </svg>
  );
}
