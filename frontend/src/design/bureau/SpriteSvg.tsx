import type { ReactNode } from "react";
import { type Sprite, tracer } from "../../lib/bureau/sprites/grille";
import { LISERE, lueur, variable } from "../../lib/bureau/sprites/jeton";

interface SpriteSvgProps {
  sprite: Sprite;
  /** Taille réelle à l'écran, en pixels CSS. */
  largeur: number;
  hauteur: number;
  /** Ce qui se dessine par-dessus, dans la même grille (une scène d'écran). */
  children?: ReactNode;
  "data-sprite"?: string;
}

/**
 * Un sprite du Bureau (ticket-727) : un `<path>` par jeton et par calque, la couleur
 * en variable CSS. Le calque garde sa classe d'animation (`anim-tape`, `anim-lueur`).
 * `overflow-visible` : les cheveux et le contour débordent de la grille.
 */
export default function SpriteSvg({ sprite, largeur, hauteur, children, ...rest }: SpriteSvgProps) {
  return (
    <svg
      width={largeur}
      height={hauteur}
      viewBox={`0 0 ${sprite.w} ${sprite.h}`}
      shapeRendering="crispEdges"
      aria-hidden="true"
      className="overflow-visible"
      data-sprite={rest["data-sprite"]}
    >
      {sprite.calques.map(({ g, classe }, i) => {
        const { fond, lisere, lueurs } = tracer(g);
        return (
          <g key={i} className={classe || undefined}>
            {fond.map(({ jeton, d }) => (
              <path key={jeton} d={d} style={{ fill: variable(jeton) }} />
            ))}
            {lisere && <path d={lisere} style={LISERE} />}
            {lueurs.map(({ etat, palier, d }) => (
              <path key={`${etat}${palier}`} d={d} style={lueur(etat, palier)} />
            ))}
          </g>
        );
      })}
      {children}
    </svg>
  );
}
