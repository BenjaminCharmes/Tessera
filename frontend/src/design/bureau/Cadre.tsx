import type { ImageDuCadre } from "../../lib/bureau/cadre";

interface CadreProps {
  /** Le tableau : tiré du nom de la pièce par `imageDuCadre`, jamais un état. */
  image: ImageDuCadre;
}

/** Le tableau, grille 8 × 10 dans le cadre : un paysage, un soleil, un champ, un portrait abstrait. */
function Toile({ image }: CadreProps) {
  switch (image) {
    case 0:
      return (
        <>
          <rect x="1" y="1" width="8" height="10" className="fill-(--sprite-toile-1)" />
          <rect x="1" y="7" width="8" height="4" className="fill-(--sprite-toile-2)" />
          <rect x="6" y="2" width="2" height="2" className="fill-(--sprite-toile-3)" />
        </>
      );
    case 1:
      return (
        <>
          <rect x="1" y="1" width="8" height="10" className="fill-(--sprite-toile-4)" />
          <rect x="3" y="3" width="4" height="4" className="fill-(--sprite-toile-3)" />
          <rect x="1" y="9" width="8" height="2" className="fill-(--sprite-toile-2)" />
        </>
      );
    case 2:
      return (
        <>
          <rect x="1" y="1" width="8" height="10" className="fill-(--sprite-toile-3)" />
          <rect x="1" y="4" width="8" height="2" className="fill-(--sprite-toile-2)" />
          <rect x="1" y="8" width="8" height="3" className="fill-(--sprite-toile-1)" />
        </>
      );
    default:
      return (
        <>
          <rect x="1" y="1" width="8" height="10" className="fill-(--sprite-toile-2)" />
          <rect x="1" y="1" width="4" height="5" className="fill-(--sprite-toile-4)" />
          <rect x="5" y="6" width="4" height="5" className="fill-(--sprite-toile-1)" />
        </>
      );
  }
}

/**
 * Un cadre accroché au mur, grille 10 × 12 (20 × 24 px). Du mobilier fixe, sans état
 * (ADR-058) : seule l'image varie d'une pièce à l'autre.
 */
export default function Cadre({ image }: CadreProps) {
  return (
    <svg
      width="20"
      height="24"
      viewBox="0 0 10 12"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="cadre"
      data-image={image}
    >
      <rect x="0" y="0" width="10" height="12" className="fill-(--sprite-cadre-bois)" />
      <Toile image={image} />
    </svg>
  );
}
