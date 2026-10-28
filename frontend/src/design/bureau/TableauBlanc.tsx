import type { EtatCase } from "../../lib/bureau/criteres";
import { TON_CASE } from "./tons";

interface TableauBlancProps {
  /** Une entrée par critère, dans l'ordre du ticket. Vide : le tableau reste vierge. */
  cases: readonly EtatCase[];
}

/** Six lignes par colonne ; au-delà de six critères, une seconde colonne, puis on s'arrête. */
const LIGNES_PAR_COLONNE = 6;
const CASES_MAX = 2 * LIGNES_PAR_COLONNE;
/** Une ligne tous les quatre pixels : une case de 3 × 3 et sa marge. */
const PAS = 4;

/** La marque d'une case cochée et d'une case refusée, en pixels de la case 3 × 3. */
const COCHE = [
  [2, 0],
  [0, 1],
  [2, 1],
  [1, 2],
] as const;
const CROIX = [
  [0, 0],
  [2, 0],
  [1, 1],
  [0, 2],
  [2, 2],
] as const;

function Case({ x, y, etat }: { x: number; y: number; etat: EtatCase }) {
  const marque = etat === "passe" ? COCHE : etat === "echoue" ? CROIX : null;
  return (
    <>
      <rect x={x} y={y} width="3" height="3" className={TON_CASE.attente} />
      <rect
        x={x + 1}
        y={y + 1}
        width="1"
        height="1"
        className="fill-(--sprite-tableau)"
      />
      {marque && (
        <>
          <rect
            x={x}
            y={y}
            width="3"
            height="3"
            className="fill-(--sprite-tableau)"
          />
          {marque.map(([dx, dy]) => (
            <rect
              key={`${dx}-${dy}`}
              x={x + dx}
              y={y + dy}
              width="1"
              height="1"
              className={TON_CASE[etat]}
            />
          ))}
        </>
      )}
    </>
  );
}

/**
 * Le tableau blanc au mur de la pièce, grille 44 × 27 (88 × 54 px). Une case et une
 * ligne par critère : case vide et ligne grise tant que rien n'est jugé, case cochée
 * et ligne verte si le critère passe, croix et ligne rouge sinon (ADR-058). Le
 * libellé accessible est porté par l'objet qui l'enveloppe. Il faisait 132 px de
 * large : rétréci et rehaussé, il laisse au mur la place de trois fenêtres et d'une
 * bibliothèque, et ses cases se lisent (ticket-627). La sixième case touchait le
 * cadre : une ligne de marge en bas, comme en haut (ticket-634).
 */
export default function TableauBlanc({ cases }: TableauBlancProps) {
  const colonnes = cases.length > LIGNES_PAR_COLONNE ? 2 : 1;
  const largeur = colonnes === 2 ? 15 : 36;
  return (
    <svg
      width="88"
      height="54"
      viewBox="0 0 44 27"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="tableau-blanc"
    >
      <rect
        x="0"
        y="0"
        width="44"
        height="27"
        className="fill-(--sprite-tableau-cadre)"
      />
      <rect
        x="1"
        y="1"
        width="42"
        height="25"
        className="fill-(--sprite-tableau)"
      />
      {cases.slice(0, CASES_MAX).map((etat, i) => {
        const x = 2 + Math.floor(i / LIGNES_PAR_COLONNE) * 21;
        const y = 2 + (i % LIGNES_PAR_COLONNE) * PAS;
        return (
          <g key={i} data-case={etat}>
            <Case x={x} y={y} etat={etat} />
            <rect
              x={x + 4}
              y={y + 1}
              width={largeur}
              height="1"
              className={TON_CASE[etat]}
            />
          </g>
        );
      })}
    </svg>
  );
}
