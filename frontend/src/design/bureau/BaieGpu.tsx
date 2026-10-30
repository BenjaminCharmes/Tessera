/** Ce que la baie d'Ollama dit : prêt à répondre, ou tenu à l'écart par le disjoncteur. */
export type EtatGpu = "disponible" | "refroidissement";

/** Le voyant : bleu pour l'activité, ambre pour l'attente (ADR-026). Classes en toutes lettres pour Tailwind. */
const TON_GPU: Record<EtatGpu, string> = {
  disponible: "fill-blue-400",
  refroidissement: "fill-amber-400 anim-gyro",
};

const CARTES = [6, 12, 18];

interface BaieGpuProps {
  etat: EtatGpu;
}

/**
 * La baie du serveur de modèles locaux (Ollama), grille 16 × 30 — ticket-726 :
 * plus large qu'une baie de service, trois cartes graphiques en façade. Le corps
 * est du mobilier ; seul le voyant rend un état, celui du disjoncteur du
 * ticket-380, et il ne clignote qu'en refroidissement (coupé sous
 * `prefers-reduced-motion`, comme le gyrophare).
 */
export default function BaieGpu({ etat }: BaieGpuProps) {
  return (
    <svg
      width="48"
      height="90"
      viewBox="0 0 16 30"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="baie-gpu"
      data-etat={etat}
    >
      <rect x="0" y="0" width="16" height="30" className="fill-(--sprite-metal-ombre)" />
      <rect x="1" y="1" width="14" height="28" className="fill-(--sprite-metal)" />
      <rect x="2" y="2" width="12" height="3" className="fill-(--sprite-metal-ombre)" />
      <rect x="12" y="3" width="1" height="1" className={TON_GPU[etat]} data-voyant={etat} />
      {CARTES.map((y) => (
        <g key={y}>
          <rect x="2" y={y} width="12" height="4" className="fill-(--sprite-metal-ombre)" />
          {[3, 5, 7, 9, 11].map((x) => (
            <rect key={x} x={x} y={y + 1} width="1" height="2" className="fill-(--sprite-dalle-trou)" />
          ))}
        </g>
      ))}
      <rect x="13" y="27" width="1" height="1" className="fill-(--sprite-metal-clair)" />
    </svg>
  );
}
