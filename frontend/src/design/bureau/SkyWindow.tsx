import type { DayMoment } from "../../lib/bureau/dayMoment";

interface SkyWindowProps {
  /** Le ciel derrière la vitre : clair, ou nuit avec des étoiles. */
  moment: DayMoment;
  /** Le soleil : une seule fenêtre du Bureau le porte. */
  soleil?: boolean;
  /** De jour, zéro à deux petits nuages. */
  nuages?: 0 | 1 | 2;
}

/** Un nuage de 4 × 2 unités, sa bosse au-dessus. */
function Nuage({ x, y }: { x: number; y: number }) {
  return (
    <g data-detail="nuage" className="fill-(--sprite-nuage)">
      <rect x={x} y={y + 1} width="4" height="1" />
      <rect x={x + 1} y={y} width="2" height="1" />
    </g>
  );
}

/**
 * Une fenêtre au mur, grille 20 × 12 (60 × 36 px). Elle rend l'heure locale que
 * l'horloge de la vue donne (ADR-058) : de 7 h à 19 h un ciel clair, sinon un ciel
 * de nuit et quatre étoiles. Fixe, sans animation.
 */
export default function SkyWindow({ moment, soleil = false, nuages = 0 }: SkyWindowProps) {
  const jour = moment === "jour";
  return (
    <svg
      width="60"
      height="36"
      viewBox="0 0 20 12"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="fenetre"
      data-moment={moment}
    >
      <rect x="0" y="0" width="20" height="12" className="fill-(--sprite-fenetre-cadre)" />
      <rect
        x="1"
        y="1"
        width="18"
        height="10"
        className={jour ? "fill-(--sprite-ciel-jour)" : "fill-(--sprite-ciel-nuit)"}
      />
      {jour ? (
        <>
          {soleil && <rect data-detail="soleil" x="13" y="2" width="3" height="3" className="fill-(--sprite-soleil)" />}
          {nuages >= 1 && <Nuage x={2} y={3} />}
          {nuages >= 2 && <Nuage x={13} y={7} />}
        </>
      ) : (
        <g data-detail="etoiles" className="fill-(--sprite-etoile)">
          <rect x="4" y="3" width="1" height="1" />
          <rect x="6" y="7" width="1" height="1" />
          <rect x="14" y="3" width="1" height="1" />
          <rect x="16" y="8" width="1" height="1" />
        </g>
      )}
      <rect x="9" y="1" width="2" height="10" className="fill-(--sprite-fenetre-cadre)" />
    </svg>
  );
}
