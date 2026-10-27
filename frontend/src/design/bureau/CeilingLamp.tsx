interface CeilingLampProps {
  /** Allumé la nuit, avec un halo jaune doux dessous ; éteint le jour, le plafonnier reste au plafond. */
  allume: boolean;
}

/**
 * Un plafonnier, grille 12 × 8 (36 × 24 px). Allumé quand il fait nuit à l'heure
 * de la vue (ADR-058) ; le halo déborde de la grille, sans capter la souris.
 */
export default function CeilingLamp({ allume }: CeilingLampProps) {
  return (
    <svg
      width="36"
      height="24"
      viewBox="0 0 12 8"
      shapeRendering="crispEdges"
      aria-hidden="true"
      className="pointer-events-none overflow-visible"
      data-sprite="plafonnier"
      data-allume={allume}
    >
      {allume && <ellipse data-detail="halo" cx="6" cy="8" rx="11" ry="8" className="fill-(--sprite-halo)" />}
      <rect x="5" y="0" width="2" height="2" className="fill-(--sprite-fenetre-cadre)" />
      <rect x="2" y="2" width="8" height="2" className="fill-(--sprite-fenetre-cadre)" />
      <rect
        x="3"
        y="4"
        width="6"
        height="1"
        className={allume ? "fill-(--sprite-plafonnier)" : "fill-(--sprite-cadre-fond)"}
      />
    </svg>
  );
}
