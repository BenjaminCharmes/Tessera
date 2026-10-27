/**
 * La machine à café de la salle de pause, grille 12 × 16. Du mobilier : elle
 * se dessine toujours, sans vapeur ni voyant, car rien ne dit qu'on s'en sert.
 */
export default function MachineACafe() {
  return (
    <svg
      width="36"
      height="48"
      viewBox="0 0 12 16"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="machine-a-cafe"
    >
      <rect x="1" y="0" width="10" height="14" className="fill-(--sprite-machine)" />
      <rect x="1" y="12" width="10" height="2" className="fill-(--sprite-machine-ombre)" />
      <rect x="3" y="2" width="6" height="3" className="fill-(--sprite-machine-ombre)" />
      <rect x="5" y="6" width="2" height="2" className="fill-(--sprite-machine-ombre)" />
      <rect x="4" y="9" width="4" height="3" className="fill-(--sprite-tasse)" />
      <rect x="0" y="14" width="12" height="2" className="fill-(--sprite-machine-ombre)" />
    </svg>
  );
}
