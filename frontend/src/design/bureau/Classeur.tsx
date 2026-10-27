/** Un classeur à tiroirs, grille 10 × 16 (30 × 48 px) : trois tiroirs et leurs poignées. Du mobilier fixe (ADR-058). */
export default function Classeur() {
  const tiroirs = [1, 6, 11] as const;
  return (
    <svg
      width="30"
      height="48"
      viewBox="0 0 10 16"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="classeur"
    >
      <rect x="0" y="0" width="10" height="16" className="fill-(--sprite-classeur-ombre)" />
      {tiroirs.map((y) => (
        <g key={y}>
          <rect x="1" y={y} width="8" height="4" className="fill-(--sprite-classeur)" />
          <rect x="4" y={y + 1} width="2" height="1" className="fill-(--sprite-classeur-ombre)" />
        </g>
      ))}
    </svg>
  );
}
