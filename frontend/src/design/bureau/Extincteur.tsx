/**
 * L'extincteur, posé contre le mur, grille 6 × 14. Du mobilier : fixe, sans
 * voyant. Son rouge est un jeton de sprite, pas une teinte d'état.
 */
export default function Extincteur() {
  return (
    <svg
      width="18"
      height="42"
      viewBox="0 0 6 14"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="extincteur"
    >
      <rect x="1" y="0" width="3" height="1" className="fill-(--sprite-metal-clair)" />
      <rect x="4" y="1" width="2" height="1" className="fill-(--sprite-metal-clair)" />
      <rect x="2" y="1" width="2" height="2" className="fill-(--sprite-metal)" />
      <rect x="1" y="3" width="4" height="11" className="fill-(--sprite-extincteur)" />
      <rect x="4" y="3" width="1" height="11" className="fill-(--sprite-extincteur-ombre)" />
      <rect x="1" y="7" width="3" height="3" className="fill-(--sprite-badge)" />
    </svg>
  );
}
