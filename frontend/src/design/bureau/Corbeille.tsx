import type { BoulesDeLaCorbeille } from "../../lib/bureau/corbeille";
import { corbeille } from "../../lib/bureau/sprites/objets";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

interface CorbeilleProps {
  /** Une boule de papier par refus du reviewer, trois au plus. */
  boules: BoulesDeLaCorbeille;
}

const dessin = memoise(corbeille);

/**
 * La corbeille, grille 20 × 24 (ticket-727) : un seau perforé, et une boule de papier
 * froissé par refus du reviewer. Vide, elle reste une corbeille (ADR-058).
 */
export default function Corbeille({ boules }: CorbeilleProps) {
  return <SpriteSvg sprite={dessin(boules)} largeur={20} hauteur={24} data-sprite="corbeille" data-boules={boules} />;
}
