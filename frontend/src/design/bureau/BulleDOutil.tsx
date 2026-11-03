interface BulleDOutilProps {
  phrase: string;
}

/**
 * La bulle d'un agent qui travaille : ce qu'il fait là, en une ligne. Même
 * teinte que l'état « actif » (bleu) ; elle ne se dessine que sur un appel
 * d'outil récent, donc elle rend un fait que le flux de run fournit (ADR-058).
 */
export default function BulleDOutil({ phrase }: BulleDOutilProps) {
  return (
    <span
      data-testid="bulle-outil"
      aria-hidden="true"
      className="inline-block max-w-full truncate whitespace-nowrap rounded-full bg-blue-500/12 px-1.5 text-mini font-medium text-blue-300"
    >
      {phrase}
    </span>
  );
}
