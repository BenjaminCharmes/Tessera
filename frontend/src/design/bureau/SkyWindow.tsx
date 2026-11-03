import type { DayMoment } from "../../lib/bureau/dayMoment";
import { fenetre } from "../../lib/bureau/sprites/mur";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

interface SkyWindowProps {
  /** Le ciel derrière la vitre : clair, ou nuit avec des étoiles. */
  moment: DayMoment;
  /** Le soleil : une seule fenêtre du Bureau le porte ; la nuit, elle porte la lune. */
  soleil?: boolean;
  /** De jour, zéro à deux nuages. */
  nuages?: 0 | 1 | 2;
}

const dessin = memoise((jour: boolean, soleil: boolean, nuages: 0 | 1 | 2) => fenetre({ jour, soleil, nuages }));

/**
 * Une fenêtre, grille 40 × 24 (60 × 36 px ; ticket-727) : ciel en dégradé à l'heure de la
 * vue, soleil ou lune, nuages, étoiles. Le ciel est une donnée, pas un état (ADR-058).
 */
export default function SkyWindow({ moment, soleil = false, nuages = 0 }: SkyWindowProps) {
  const jour = moment === "jour";
  const ciel = jour ? nuages : 0;
  return (
    <SpriteSvg
      sprite={dessin(jour, soleil, ciel)}
      largeur={60}
      hauteur={36}
      data-sprite="fenetre"
      data-moment={moment}
      data-soleil={soleil}
      data-nuages={ciel}
    />
  );
}
