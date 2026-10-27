import type { Physique } from "../../lib/bureau/physique";
import { FILL_CHEVEUX, FILL_PEAU } from "./tons";

interface TeteProps {
  physique: Physique;
  /** Coin haut-gauche du visage dans la grille de la pose : la tête fait 6 × 4 dans les deux. */
  x: number;
  y: number;
}

/** Les cheveux d'une coiffure, dessinés derrière le visage. */
function Cheveux({ physique, x, y }: TeteProps) {
  const classe = FILL_CHEVEUX[physique.cheveux];
  const { coiffure } = physique;
  return (
    <>
      {coiffure === "long" && (
        <>
          <rect x={x - 1} y={y - 1} width="1" height="7" className={classe} />
          <rect x={x + 6} y={y - 1} width="1" height="7" className={classe} />
        </>
      )}
      {coiffure === "carre" && (
        <>
          <rect x={x - 1} y={y - 1} width="1" height="4" className={classe} />
          <rect x={x + 6} y={y - 1} width="1" height="4" className={classe} />
        </>
      )}
      {coiffure === "chauve" ? (
        <>
          <rect x={x} y={y - 1} width="1" height="2" className={classe} />
          <rect x={x + 5} y={y - 1} width="1" height="2" className={classe} />
        </>
      ) : (
        <rect x={x} y={y - 2} width="6" height="2" className={classe} />
      )}
    </>
  );
}

/**
 * Les tempes de la coupe courte : un carré de cheveux de chaque côté, sur la première
 * ligne du visage. Dessinées après le visage, qui les couvrirait sinon ; hors des yeux
 * (colonnes x + 1 et x + 4).
 */
function Tempes({ physique, x, y }: TeteProps) {
  if (physique.coiffure !== "court") return null;
  const classe = FILL_CHEVEUX[physique.cheveux];
  return (
    <>
      <rect data-partie="tempe" x={x} y={y} width="1" height="1" className={classe} />
      <rect data-partie="tempe" x={x + 5} y={y} width="1" height="1" className={classe} />
    </>
  );
}

/** La tête d'un agent : cheveux, visage de 6 unités de large, yeux. Même dessin assis et debout. */
export default function Tete({ physique, x, y }: TeteProps) {
  return (
    <>
      <Cheveux physique={physique} x={x} y={y} />
      <rect
        data-partie="tete"
        x={x}
        y={y}
        width="6"
        height="4"
        className={FILL_PEAU[physique.peau]}
      />
      <Tempes physique={physique} x={x} y={y} />
      {physique.coiffure === "chauve" && (
        <rect x={x + 1} y={y - 1} width="4" height="1" className={FILL_PEAU[physique.peau]} />
      )}
      <rect x={x + 1} y={y + 1} width="1" height="1" className="fill-zinc-900" />
      <rect x={x + 4} y={y + 1} width="1" height="1" className="fill-zinc-900" />
    </>
  );
}
