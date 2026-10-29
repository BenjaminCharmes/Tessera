/**
 * La porte coupe-feu : un vantail métallique et son lecteur de badge, grille
 * 14 × 18. Du mobilier : fixe, sans voyant — le lecteur ne rend aucun état.
 */
export default function PorteCoupeFeu() {
  return (
    <svg
      width="42"
      height="54"
      viewBox="0 0 14 18"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="porte-coupe-feu"
    >
      <rect x="0" y="0" width="11" height="18" className="fill-(--sprite-metal-ombre)" />
      <rect x="1" y="1" width="9" height="17" className="fill-(--sprite-metal)" />
      <rect x="2" y="3" width="7" height="3" className="fill-(--sprite-metal-ombre)" />
      <rect x="2" y="12" width="7" height="1" className="fill-(--sprite-metal-ombre)" />
      <rect x="8" y="9" width="1" height="2" className="fill-(--sprite-metal-clair)" />
      <rect x="11" y="7" width="3" height="5" className="fill-(--sprite-metal-ombre)" />
      <rect x="12" y="8" width="1" height="2" className="fill-(--sprite-badge)" />
    </svg>
  );
}
