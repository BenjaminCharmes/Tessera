import type { Physique, Tenue } from "../../lib/bureau/physique";
import Personnage from "./Personnage";

interface BureauEnBoisProps {
  /** Qui s'y assoit : la tenue et le physique de la figure de la salle. */
  tenue: Tenue;
  physique: Physique;
}

/**
 * Le bureau en bois d'une salle commune, grille 16 × 18 comme un poste : la
 * figure de la salle (le directeur, la recruteuse) assise derrière. C'est du
 * mobilier — fixe, sans écran ni voyant ; ce que la salle dit vient de ses
 * occupants (ADR-058).
 */
export default function BureauEnBois({ tenue, physique }: BureauEnBoisProps) {
  return (
    <svg
      width="56"
      height="63"
      viewBox="0 0 16 18"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="bureau-en-bois"
    >
      <Personnage tenue={tenue} physique={physique} />
      <rect x="1" y="12" width="14" height="2" className="fill-(--sprite-table)" />
      <rect x="1" y="14" width="14" height="1" className="fill-(--sprite-table-ombre)" />
      <rect x="2" y="15" width="1" height="3" className="fill-(--sprite-table-ombre)" />
      <rect x="13" y="15" width="1" height="3" className="fill-(--sprite-table-ombre)" />
    </svg>
  );
}
