/**
 * Une étagère murale, grille 16 × 10 (32 × 20 px) : une planche, une petite plante
 * et deux livres. Du mobilier fixe, sans état (ADR-058).
 */
export default function Etagere() {
  return (
    <svg
      width="32"
      height="20"
      viewBox="0 0 16 10"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="etagere"
    >
      <rect x="1" y="1" width="2" height="2" className="fill-(--sprite-plante)" />
      <rect x="3" y="0" width="2" height="3" className="fill-(--sprite-plante-ombre)" />
      <rect x="2" y="3" width="4" height="3" className="fill-(--sprite-pot)" />
      <rect x="8" y="2" width="2" height="4" className="fill-(--sprite-livre-1)" />
      <rect x="10" y="3" width="3" height="3" className="fill-(--sprite-livre-2)" />
      <rect x="0" y="6" width="16" height="2" className="fill-(--sprite-etagere)" />
      <rect x="1" y="8" width="2" height="2" className="fill-(--sprite-etagere)" />
      <rect x="13" y="8" width="2" height="2" className="fill-(--sprite-etagere)" />
    </svg>
  );
}
