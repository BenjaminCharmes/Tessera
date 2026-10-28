/** Un livre : abscisse, décalage depuis le haut de la rangée, largeur, hauteur, teinte. */
type Livre = readonly [
  x: number,
  dy: number,
  largeur: number,
  hauteur: number,
  teinte: 1 | 2 | 3,
];

const TEINTE: Record<Livre[4], string> = {
  1: "fill-(--sprite-livre-1)",
  2: "fill-(--sprite-livre-2)",
  3: "fill-(--sprite-livre-3)",
};

/**
 * Trois rangées différentes : des livres identiques d'une étagère à l'autre se
 * lisaient comme un motif, pas comme une bibliothèque (ticket-627).
 */
const RANGEES: readonly { y: number; livres: readonly Livre[] }[] = [
  {
    y: 2,
    livres: [
      [2, 0, 2, 4, 1],
      [4, 1, 2, 3, 2],
      [6, 0, 1, 4, 3],
      [8, 1, 2, 3, 1],
      [11, 0, 2, 4, 3],
    ],
  },
  {
    y: 7,
    livres: [
      [2, 1, 1, 3, 3],
      [3, 0, 2, 4, 2],
      [5, 0, 1, 4, 1],
      [7, 2, 3, 2, 3],
      [11, 1, 1, 3, 2],
      [12, 0, 2, 4, 1],
    ],
  },
  {
    y: 12,
    livres: [
      [2, 0, 2, 4, 2],
      [5, 1, 1, 3, 1],
      [6, 0, 2, 4, 3],
      [9, 1, 2, 3, 2],
      [12, 0, 1, 4, 1],
    ],
  },
];

/**
 * Une bibliothèque basse, grille 16 × 18 (48 × 54 px) : trois étagères de livres, la
 * dernière formant le bas du meuble. Du mobilier fixe (ADR-058).
 */
export default function Bibliotheque() {
  return (
    <svg
      width="48"
      height="54"
      viewBox="0 0 16 18"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="bibliotheque"
    >
      <rect
        x="0"
        y="0"
        width="16"
        height="18"
        className="fill-(--sprite-table-ombre)"
      />
      <rect
        x="1"
        y="1"
        width="14"
        height="16"
        className="fill-(--sprite-table)"
      />
      {RANGEES.map(({ y, livres }) => (
        <g key={y}>
          {livres.map(([x, dy, largeur, hauteur, teinte]) => (
            <rect
              key={x}
              x={x}
              y={y + dy}
              width={largeur}
              height={hauteur}
              className={TEINTE[teinte]}
            />
          ))}
          <rect
            x="1"
            y={y + 4}
            width="14"
            height="1"
            className="fill-(--sprite-table-ombre)"
          />
        </g>
      ))}
    </svg>
  );
}
