import { type EspeceDePlante, plante } from "../../lib/bureau/sprites/mobilier";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

export type { EspeceDePlante };

interface PlanteProps {
  espece?: EspeceDePlante;
}

const dessin = memoise(plante);

/**
 * Une plante, posée dans un coin de pièce ou de salle (ticket-727) : en pot et cactus
 * 16 × 20, ficus 16 × 32. Du mobilier fixe (ADR-058).
 */
export default function Plante({ espece = "pot" }: PlanteProps) {
  return (
    <SpriteSvg
      sprite={dessin(espece)}
      largeur={40}
      hauteur={espece === "ficus" ? 80 : 50}
      data-sprite="plante"
      data-espece={espece}
    />
  );
}
