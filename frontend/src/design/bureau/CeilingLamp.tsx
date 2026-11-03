import { useId } from "react";
import { plafonnier } from "../../lib/bureau/sprites/mur";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

interface CeilingLampProps {
  /** Allumé la nuit, ou par l'interrupteur ; éteint, le plafonnier reste au plafond. */
  allume: boolean;
  /** En journée, la lumière se voit moins : le cône est plus pâle (ticket-663). */
  jour?: boolean;
}

const dessin = memoise(plafonnier);

/**
 * Un plafonnier, grille 24 × 16 (36 × 24 px ; ticket-727) : abat-jour émaillé, diffuseur
 * qui s'éclaire. Allumé, il projette un cône de lumière qui s'élargit et s'efface en
 * descendant, plus pâle de jour. Le cône déborde de la grille, sans capter la souris
 * (ADR-058 : il dit que la lampe est allumée).
 */
export default function CeilingLamp({ allume, jour = false }: CeilingLampProps) {
  const degrade = useId();
  const halo = allume && (
    <>
      <defs>
        <linearGradient id={degrade} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--sprite-halo-coeur)" stopOpacity={jour ? 0.35 : 0.7} />
          <stop offset="1" stopColor="var(--sprite-halo-coeur)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon
        data-detail="halo"
        points="6,11 18,11 44,68 -20,68"
        fill={`url(#${degrade})`}
        shapeRendering="geometricPrecision"
      />
    </>
  );
  return (
    <SpriteSvg
      sprite={dessin(allume)}
      largeur={36}
      hauteur={24}
      dessous={halo}
      className="pointer-events-none"
      data-sprite="plafonnier"
      data-allume={allume}
    />
  );
}
