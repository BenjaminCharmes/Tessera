interface InterrupteurProps {
  allume: boolean;
}

/** Un interrupteur mural, grille 6 × 9 (12 × 18 px) : la touche en haut quand la lumière est allumée. */
export default function Interrupteur({ allume }: InterrupteurProps) {
  return (
    <svg
      width="12"
      height="18"
      viewBox="0 0 6 9"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="interrupteur"
      data-allume={allume}
    >
      <rect x="0" y="0" width="6" height="9" className="fill-(--sprite-interrupteur)" />
      <rect x="2" y={allume ? 2 : 4} width="2" height="3" className="fill-(--sprite-interrupteur-touche)" />
    </svg>
  );
}
