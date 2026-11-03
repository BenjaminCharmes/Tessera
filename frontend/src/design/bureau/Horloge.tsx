import { aiguillesDeLHorloge } from "../../lib/bureau/aiguilles";
import { horloge } from "../../lib/bureau/sprites/mur";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

interface HorlogeProps {
  /** L'horloge unique de la vue, en millisecondes : les aiguilles en donnent l'heure locale. */
  maintenant: number;
}

const dessin = memoise(horloge);

/**
 * L'horloge murale, grille 16 × 16 (ticket-727) : cadran rond, quatre repères, deux
 * aiguilles au pixel près. Elles disent l'heure de l'horloge de la vue, comme le ciel
 * des fenêtres (ADR-058) : elle ne tourne qu'avec elle, sans mouvement propre.
 */
export default function Horloge({ maintenant }: HorlogeProps) {
  const { heure, minute } = aiguillesDeLHorloge(maintenant);
  const date = new Date(maintenant);
  return (
    <SpriteSvg
      sprite={dessin(date.getHours(), date.getMinutes())}
      largeur={16}
      hauteur={16}
      data-sprite="horloge"
      data-angle-heure={heure}
      data-angle-minute={minute}
    />
  );
}
