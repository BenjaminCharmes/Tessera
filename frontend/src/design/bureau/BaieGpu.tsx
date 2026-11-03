import { type EtatGpu, baieGpu } from "../../lib/bureau/sprites/produit";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

export type { EtatGpu };

interface BaieGpuProps {
  etat: EtatGpu;
}

const dessin = memoise(baieGpu);

/**
 * La baie du serveur de modèles locaux (Ollama), grille 32 × 60 (ticket-726,
 * ticket-727) : plus large qu'une baie de service, trois cartes graphiques à deux
 * ventilateurs. Le corps est du mobilier ; seul le voyant rend un état, celui du
 * disjoncteur du ticket-380 : bleu disponible, ambre en refroidissement, où il
 * clignote, sauf sous mouvement réduit.
 */
export default function BaieGpu({ etat }: BaieGpuProps) {
  return <SpriteSvg sprite={dessin(etat)} largeur={48} hauteur={90} data-sprite="baie-gpu" data-etat={etat} />;
}
