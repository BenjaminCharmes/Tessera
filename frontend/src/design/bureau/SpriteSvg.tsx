import { type CSSProperties, type ReactNode, useLayoutEffect, useMemo } from "react";
import type { Sprite } from "../../lib/bureau/sprites/grille";
import { inscrire, instancesDuSprite, liberer } from "../../lib/bureau/sprites/symboles";

/** Les attributs `data-*` que la vue et les tests lisent sur le sprite : ce qu'il rend. */
type Donnees = { [cle: `data-${string}`]: string | number | boolean | undefined };

type SpriteSvgProps = Donnees & {
  sprite: Sprite;
  /** Taille réelle à l'écran, en pixels CSS. */
  largeur: number;
  hauteur: number;
  /** Ce qui se dessine par-dessous les calques, dans la même grille (un halo). */
  dessous?: ReactNode;
  /** Ce qui se dessine par-dessus, dans la même grille (une scène d'écran). */
  children?: ReactNode;
  className?: string;
};

/**
 * Un sprite du Bureau (ticket-727) : un `<use>` par calque, qui pose son symbole
 * du `<defs>` commun (`DefsDuBureau`). Le `<use>` garde la classe d'animation du
 * calque (`anim-tape`, `anim-lueur`) et lie les couleurs propres à l'agent.
 * `overflow-visible` : les cheveux et le contour débordent de la grille.
 */
export default function SpriteSvg({ sprite, largeur, hauteur, dessous, children, className = "", ...donnees }: SpriteSvgProps) {
  const instances = useMemo(() => instancesDuSprite(sprite), [sprite]);
  useLayoutEffect(() => {
    for (const { symbole } of instances) inscrire(symbole);
    return () => {
      for (const { symbole } of instances) liberer(symbole.id);
    };
  }, [instances]);
  return (
    <svg
      width={largeur}
      height={hauteur}
      viewBox={`0 0 ${sprite.w} ${sprite.h}`}
      shapeRendering="crispEdges"
      aria-hidden="true"
      className={`overflow-visible ${className}`.trim()}
      {...donnees}
    >
      {dessous}
      {instances.map(({ symbole, classe, style }, i) => (
        <use
          key={i}
          href={`#${symbole.id}`}
          width={symbole.w}
          height={symbole.h}
          className={classe || undefined}
          style={style as CSSProperties}
        />
      ))}
      {children}
    </svg>
  );
}
