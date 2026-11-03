import { interrupteur } from "../../lib/bureau/sprites/mur";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

interface InterrupteurProps {
  allume: boolean;
}

const dessin = memoise(interrupteur);

/**
 * Un interrupteur mural, grille 12 × 18 (ticket-727) : la bascule s'enfonce du côté
 * éteint. Il passe par `Agrandi` comme tout sprite : 5,5 × 8,25 px bruts, environ
 * 6 × 9 px à l'échelle de 1536 (ticket-631).
 */
export default function Interrupteur({ allume }: InterrupteurProps) {
  return <SpriteSvg sprite={dessin(allume)} largeur={5.5} hauteur={8.25} data-sprite="interrupteur" data-allume={allume} />;
}
