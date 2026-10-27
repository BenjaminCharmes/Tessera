/** Une bibliothèque basse, grille 16 × 18 (48 × 54 px) : trois étagères de livres. Du mobilier fixe (ADR-058). */
export default function Bibliotheque() {
  const etageres = [2, 8, 14] as const;
  return (
    <svg
      width="48"
      height="54"
      viewBox="0 0 16 18"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="bibliotheque"
    >
      <rect x="0" y="0" width="16" height="18" className="fill-(--sprite-table-ombre)" />
      <rect x="1" y="1" width="14" height="16" className="fill-(--sprite-table)" />
      {etageres.map((y) => (
        <g key={y}>
          <rect x="2" y={y} width="2" height="4" className="fill-(--sprite-livre-1)" />
          <rect x="4" y={y + 1} width="2" height="3" className="fill-(--sprite-livre-2)" />
          <rect x="6" y={y} width="1" height="4" className="fill-(--sprite-livre-3)" />
          <rect x="8" y={y + 1} width="2" height="3" className="fill-(--sprite-livre-1)" />
          <rect x="11" y={y} width="2" height="4" className="fill-(--sprite-livre-3)" />
          <rect x="1" y={y + 4} width="14" height="1" className="fill-(--sprite-table-ombre)" />
        </g>
      ))}
    </svg>
  );
}
