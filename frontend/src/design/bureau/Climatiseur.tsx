const LAMES = [3, 5, 7, 9, 11, 13];

/**
 * Le climatiseur de salle : une armoire à grilles, grille 16 × 22. Du mobilier :
 * il se dessine toujours, fixe, sans voyant.
 */
export default function Climatiseur() {
  return (
    <svg
      width="48"
      height="66"
      viewBox="0 0 16 22"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="climatiseur"
    >
      <rect x="0" y="0" width="16" height="22" className="fill-(--sprite-metal-ombre)" />
      <rect x="1" y="1" width="14" height="20" className="fill-(--sprite-metal)" />
      <rect x="2" y="2" width="12" height="13" className="fill-(--sprite-metal-ombre)" />
      {LAMES.map((y) => (
        <rect key={y} x="3" y={y} width="10" height="1" className="fill-(--sprite-metal-clair)" />
      ))}
      <rect x="2" y="17" width="12" height="3" className="fill-(--sprite-metal-clair)" />
      <rect x="3" y="18" width="10" height="1" className="fill-(--sprite-metal-ombre)" />
    </svg>
  );
}
