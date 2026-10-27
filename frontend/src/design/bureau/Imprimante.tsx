/** Hauteur du dessus du meuble, en pixels avant agrandissement : la pile de dossiers s'y pose. */
export const HAUTEUR_DU_MEUBLE = 24;

/**
 * Un meuble bas et son imprimante, grille 24 × 14 (72 × 42 px). Du mobilier fixe
 * (ADR-058) : la pile des tickets en file se pose à côté de l'imprimante.
 */
export default function Imprimante() {
  return (
    <svg
      width="72"
      height="42"
      viewBox="0 0 24 14"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="imprimante"
    >
      <rect x="1" y="2" width="9" height="4" className="fill-(--sprite-classeur)" />
      <rect x="2" y="0" width="7" height="2" className="fill-(--sprite-classeur-ombre)" />
      <rect x="3" y="4" width="5" height="1" className="fill-(--sprite-feuille)" />
      <rect x="0" y="6" width="24" height="2" className="fill-(--sprite-table)" />
      <rect x="1" y="8" width="22" height="6" className="fill-(--sprite-table-ombre)" />
      <rect x="11" y="10" width="2" height="1" className="fill-(--sprite-table)" />
    </svg>
  );
}
