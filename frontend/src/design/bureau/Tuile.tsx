import { useLayoutEffect } from "react";
import { type Moment, type Motif, contenuDuMotif } from "../../lib/bureau/sprites/ambiance";
import { inscrire, liberer } from "../../lib/bureau/sprites/symboles";

interface TuileProps {
  motif: Motif;
  moment: Moment;
  /** `-z-10` dans un parent `isolate` : la surface passe sous ses enfants non positionnés. */
  className?: string;
}

/**
 * Une surface carrelée de sa tuile (sol, mur, plinthe ; ticket-727) : elle remplit
 * son parent positionné, derrière ce qu'il porte. Un `<rect>` peint du motif du
 * `<defs>` commun, quelle que soit la surface. Du mobilier : fixe, sans état (ADR-058).
 */
export default function Tuile({ motif, moment, className = "" }: TuileProps) {
  const contenu = contenuDuMotif(motif, moment);
  useLayoutEffect(() => {
    inscrire(contenu);
    return () => liberer(contenu.id);
  }, [contenu]);
  return (
    <svg
      aria-hidden="true"
      className={`pointer-events-none absolute inset-0 h-full w-full ${className}`.trim()}
      shapeRendering="crispEdges"
      data-tuile={motif}
    >
      <rect width="100%" height="100%" fill={`url(#${contenu.id})`} />
    </svg>
  );
}
