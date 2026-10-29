import { aiguillesDeLHorloge } from "../../lib/bureau/aiguilles";

interface HorlogeProps {
  /** L'horloge unique de la vue, en millisecondes : les aiguilles en donnent l'heure locale. */
  maintenant: number;
}

/**
 * L'horloge murale, grille 8 × 8 (16 × 16 px). Ses aiguilles disent l'heure de
 * l'horloge de la vue, comme le ciel des fenêtres (ADR-058) : elle ne tourne qu'avec
 * elle, sans mouvement propre.
 */
export default function Horloge({ maintenant }: HorlogeProps) {
  const { heure, minute } = aiguillesDeLHorloge(maintenant);
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 8 8"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="horloge"
    >
      <rect x="0" y="0" width="8" height="8" className="fill-(--sprite-horloge-bord)" />
      <rect x="1" y="1" width="6" height="6" className="fill-(--sprite-horloge-cadran)" />
      <rect
        data-aiguille="heure"
        data-angle={heure}
        x="3.5"
        y="2"
        width="1"
        height="2"
        transform={`rotate(${heure} 4 4)`}
        className="fill-(--sprite-horloge-aiguille)"
      />
      <rect
        data-aiguille="minute"
        data-angle={minute}
        x="3.75"
        y="1"
        width="0.5"
        height="3"
        transform={`rotate(${minute} 4 4)`}
        className="fill-(--sprite-horloge-aiguille)"
      />
    </svg>
  );
}
