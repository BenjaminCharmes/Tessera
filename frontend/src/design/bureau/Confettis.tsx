import { NOMBRE_DE_CONFETTIS, depart } from "../../lib/bureau/confettis";
import { confetti } from "../../lib/bureau/sprites/objets";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

const dessin = memoise(confetti);

/**
 * Les confettis d'une PR mergée (ticket-727) : cinq formes et cinq tons, 4 × 6 px, qui
 * tombent le temps de la fête. Sous `prefers-reduced-motion` ils ne tombent plus et
 * restent là où ils ont été lâchés.
 */
export default function Confettis() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 z-20 overflow-hidden">
      {Array.from({ length: NOMBRE_DE_CONFETTIS }, (_, i) => {
        const { left, top, delai } = depart(i);
        return (
          <span
            key={i}
            data-sprite="confetti"
            className="anim-chute absolute block"
            style={{ left, top, animationDelay: `${delai}s` }}
          >
            <SpriteSvg sprite={dessin(i % 5)} largeur={4} hauteur={6} />
          </span>
        );
      })}
    </div>
  );
}
