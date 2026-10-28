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
 * Le tableau blanc au mur de la pièce, grille 32 × 14 (96 × 42 px). Une ligne par
 * critère : grise tant que rien n'est jugé, verte si le critère passe, rouge sinon
 * (ADR-058). Le libellé accessible est porté par l'objet qui l'enveloppe.
 * Il faisait 132 px : rétréci, il laisse au mur la place de trois fenêtres et
 * d'une bibliothèque (ticket-627).
 */
export default function TableauBlanc({ cases }: TableauBlancProps) {
  const colonnes = cases.length > LIGNES_PAR_COLONNE ? 2 : 1;
  const largeur = colonnes === 2 ? 13 : 28;
  return (
    <svg
      width="96"
      height="42"
      viewBox="0 0 32 14"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="tableau-blanc"
    >
      <rect
        x="0"
        y="0"
        width="32"
        height="14"
        className="fill-(--sprite-tableau-cadre)"
      />
      <rect
        x="1"
        y="1"
        width="30"
        height="12"
        className="fill-(--sprite-tableau)"
      />
      {cases.slice(0, CASES_MAX).map((etat, i) => (
        <rect
          key={i}
          x={2 + Math.floor(i / LIGNES_PAR_COLONNE) * 15}
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
