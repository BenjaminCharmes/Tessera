import { useMemo } from "react";
import type { Physique, Tenue } from "../../lib/bureau/physique";
import { bureauEnBois } from "../../lib/bureau/sprites/communs";
import SpriteSvg from "./SpriteSvg";

interface BureauEnBoisProps {
  /** Qui s'y assoit : la tenue et le physique de la figure de la salle. */
  tenue: Tenue;
  physique: Physique;
  /** Personne derrière : le fauteuil reste, la figure est partie en visite (ticket-661). */
  vide?: boolean;
}

/**
 * Le bureau en bois d'une salle commune, grille 32 × 36 comme un poste (ticket-727) :
 * fauteuil capitonné, plateau veiné, caisson, pot à crayons, et la figure de la salle
 * (le directeur, la recruteuse) assise derrière. Du mobilier — sans écran ni voyant ;
 * ce que la salle dit vient de ses occupants (ADR-058).
 */
export default function BureauEnBois({ tenue, physique, vide = false }: BureauEnBoisProps) {
  const dessin = useMemo(() => bureauEnBois(vide ? null : { tenue, physique }), [tenue, physique, vide]);
  return <SpriteSvg sprite={dessin} largeur={56} hauteur={63} data-sprite="bureau-en-bois" data-pose={vide ? undefined : "assis"} />;
}
