const BARREAUX = Array.from({ length: 100 }, (_, i) => i * 2);

/**
 * Le chemin de câbles du plafond : un caillebotis métallique sur toute la
 * largeur du mur, grille 200 × 8. Du mobilier : fixe, sans voyant. Étiré
 * horizontalement, il garde ses barreaux au pixel près.
 */
export default function CheminDeCables() {
  return (
    <svg
      width="100%"
      height="24"
      viewBox="0 0 200 8"
      preserveAspectRatio="none"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="chemin-de-cables"
    >
      <rect x="0" y="0" width="200" height="1" className="fill-(--sprite-metal)" />
      <rect x="0" y="1" width="200" height="2" className="fill-(--sprite-metal-ombre)" />
      {BARREAUX.map((x) => (
        <rect key={x} x={x} y="1" width="1" height="1" className="fill-(--sprite-metal)" />
      ))}
      <rect x="0" y="3" width="200" height="1" className="fill-(--sprite-salle-plinthe)" />
    </svg>
  );
}
