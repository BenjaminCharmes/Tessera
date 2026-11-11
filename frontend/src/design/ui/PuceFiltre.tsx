import type { ReactNode } from "react";

/**
 * Puce de filtre à bascule — ticket-919.
 *
 * Active : fond violet (l'interaction, ADR-026), jamais texte violet.
 */
interface PuceFiltreProps {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}

export default function PuceFiltre({ active, onClick, children }: PuceFiltreProps) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`focus-violet rounded-full px-2.5 py-0.5 text-micro transition-colors ${
        active
          ? "bg-violet-500/20 text-zinc-100"
          : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200"
      }`}
    >
      {children}
    </button>
  );
}
