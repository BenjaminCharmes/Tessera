import { useId } from "react";

interface CeilingLampProps {
  /** Allumé la nuit, ou par l'interrupteur ; éteint, le plafonnier reste au plafond. */
  allume: boolean;
  /** En journée, la lumière se voit moins : le cône est plus pâle (ticket-663). */
  jour?: boolean;
}

/**
 * Un plafonnier, grille 12 × 8 (36 × 24 px). Allumé, il projette un cône de lumière
 * vers le bas, qui s'élargit et s'efface en descendant ; plus pâle de jour. Le cône
 * déborde de la grille, sans capter la souris (ADR-058 : il dit que la lampe est allumée).
 */
export default function CeilingLamp({
  allume,
  jour = false,
}: CeilingLampProps) {
  const degrade = useId();
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
      {allume && (
        <>
          <defs>
            <linearGradient id={degrade} x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="0"
                stopColor="var(--sprite-halo-coeur)"
                stopOpacity={jour ? 0.35 : 0.7}
              />
              <stop
                offset="1"
                stopColor="var(--sprite-halo-coeur)"
                stopOpacity="0"
              />
            </linearGradient>
          </defs>
          <polygon
            data-detail="halo"
            points="3,5 9,5 22,34 -10,34"
            fill={`url(#${degrade})`}
            shapeRendering="geometricPrecision"
          />
        </>
      )}
      <rect
        x="5"
        y="0"
        width="2"
        height="2"
        className="fill-(--sprite-fenetre-cadre)"
      />
      <rect
        x="2"
        y="2"
        width="8"
        height="2"
        className="fill-(--sprite-fenetre-cadre)"
      />
      <rect
        x="3"
        y="4"
        width="6"
        height="1"
        className={
          allume ? "fill-(--sprite-plafonnier)" : "fill-(--sprite-cadre-fond)"
        }
      />
    </svg>
  );
}
