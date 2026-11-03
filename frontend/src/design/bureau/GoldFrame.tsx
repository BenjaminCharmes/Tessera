import { useMemo } from "react";
import { physique } from "../../lib/bureau/physique";
import { cadreDore } from "../../lib/bureau/sprites/tableau";
import SpriteSvg from "./SpriteSvg";

interface GoldFrameProps {
  /** Le projet dont le codeur pose : son physique est celui de son poste (ticket-595). */
  projet: string;
}

/**
 * Le cadre doré de l'employé de la semaine, grille 32 × 34 (ticket-727) : baguette
 * perlée, fond de velours, buste du codeur du projet, plaque gravée. Il ne se dessine
 * que si un projet a des tickets approuvés au premier tour (ADR-058).
 */
export default function GoldFrame({ projet }: GoldFrameProps) {
  const dessin = useMemo(() => cadreDore(physique(projet, "codeur")), [projet]);
  return <SpriteSvg sprite={dessin} largeur={32} hauteur={34} data-sprite="cadre-employe" />;
}
