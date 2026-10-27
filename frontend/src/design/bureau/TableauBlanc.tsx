import type { EtatCase } from "../../lib/bureau/criteres";
import { TON_CASE } from "./tons";

interface TableauBlancProps {
  /** Une entrée par critère, dans l'ordre du ticket. Vide : le tableau reste vierge. */
  cases: readonly EtatCase[];
}

/** Six lignes par colonne ; au-delà de six critères, une seconde colonne, puis on s'arrête. */
const LIGNES_PAR_COLONNE = 6;
const CASES_MAX = 2 * LIGNES_PAR_COLONNE;

/**
 * Le tableau blanc au mur de la pièce, grille 44 × 14 (132 × 42 px). Une ligne par
 * critère : grise tant que rien n'est jugé, verte si le critère passe, rouge sinon
 * (ADR-058). Le libellé accessible est porté par l'objet qui l'enveloppe.
 */
export default function TableauBlanc({ cases }: TableauBlancProps) {
  const colonnes = cases.length > LIGNES_PAR_COLONNE ? 2 : 1;
  const largeur = colonnes === 2 ? 19 : 40;
  return (
    <svg
      width="132"
      height="42"
      viewBox="0 0 44 14"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="tableau-blanc"
    >
      <rect x="0" y="0" width="44" height="14" className="fill-(--sprite-tableau-cadre)" />
      <rect x="1" y="1" width="42" height="12" className="fill-(--sprite-tableau)" />
      {cases.slice(0, CASES_MAX).map((etat, i) => (
        <rect
          key={i}
          x={2 + Math.floor(i / LIGNES_PAR_COLONNE) * 21}
          y={2 + (i % LIGNES_PAR_COLONNE) * 2}
          width={largeur}
          height="1"
          className={TON_CASE[etat]}
          data-case={etat}
        />
      ))}
    </svg>
  );
}
