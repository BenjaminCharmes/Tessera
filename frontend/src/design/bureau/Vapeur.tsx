/**
 * La vapeur de la machine à café, grille 12 × 8. Un composant à part : la
 * machine est du mobilier fixe, la vapeur ne se dessine que quand un agent s'y
 * sert (ADR-058). Trois volutes qui montent par paliers.
 */
export default function Vapeur() {
  return (
    <svg
      width="36"
      height="24"
      viewBox="0 0 12 8"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="vapeur"
      className="anim-vapeur"
    >
      <rect x="3" y="4" width="1" height="3" className="fill-(--sprite-vapeur)" />
      <rect x="5" y="1" width="1" height="4" className="fill-(--sprite-vapeur)" />
      <rect x="8" y="3" width="1" height="3" className="fill-(--sprite-vapeur)" />
    </svg>
  );
}
