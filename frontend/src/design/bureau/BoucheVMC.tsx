/** Le régime du ventilateur : arrêté, ou plus rapide quand le projet consomme plus. */
export type RegimeVMC = "arret" | "lent" | "moyen" | "rapide";

const DUREE: Record<Exclude<RegimeVMC, "arret">, string> = {
  lent: "2.4s",
  moyen: "1.2s",
  rapide: "0.6s",
};

interface BoucheVMCProps {
  regime: RegimeVMC;
}

/**
 * La bouche de ventilation de la salle des serveurs, grille 14 × 14. Le cadre
 * est du mobilier ; l'hélice rend une donnée (ADR-058) : elle ne tourne que si
 * un service du projet tourne, d'autant plus vite que le projet consomme de
 * mémoire. `prefers-reduced-motion` l'arrête.
 */
export default function BoucheVMC({ regime }: BoucheVMCProps) {
  return (
    <svg
      width="42"
      height="42"
      viewBox="0 0 14 14"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="bouche-vmc"
      data-regime={regime}
    >
      <rect x="0" y="0" width="14" height="14" className="fill-(--sprite-metal-ombre)" />
      <rect x="1" y="1" width="12" height="12" className="fill-(--sprite-metal)" />
      <rect x="2" y="2" width="10" height="10" className="fill-(--sprite-dalle-trou)" />
      <g
        className={regime === "arret" ? undefined : "anim-helice"}
        style={regime === "arret" ? undefined : { animationDuration: DUREE[regime] }}
      >
        <rect x="6" y="3" width="2" height="3" className="fill-(--sprite-metal-clair)" />
        <rect x="6" y="8" width="2" height="3" className="fill-(--sprite-metal-clair)" />
        <rect x="3" y="6" width="3" height="2" className="fill-(--sprite-metal-clair)" />
        <rect x="8" y="6" width="3" height="2" className="fill-(--sprite-metal-clair)" />
      </g>
      <rect x="6" y="6" width="2" height="2" className="fill-(--sprite-metal-ombre)" />
      {[3, 5, 7, 9, 11].map((y) => (
        <rect key={y} x="2" y={y} width="10" height="0.5" className="fill-(--sprite-metal-ombre)" opacity="0.6" />
      ))}
    </svg>
  );
}
