import type { ReactNode } from "react";

/**
 * Pastille de compteur — ticket-919.
 *
 * Un seul gabarit pour les trois compteurs de l'appli (cloche, supervision,
 * dossiers). Le ton suit ADR-026 : les familles d'état, plus `violet` en fond
 * pour l'identité, jamais en couleur de texte.
 */
export type TonCompteur = "violet" | "zinc" | "red" | "amber" | "blue";

const TONS: Record<TonCompteur, string> = {
  violet: "bg-violet-500 text-zinc-50",
  zinc: "bg-zinc-700 text-zinc-100",
  red: "bg-red-500/20 text-red-200",
  amber: "bg-amber-500/20 text-amber-200",
  blue: "bg-blue-500/20 text-blue-200",
};

interface CompteurProps {
  ton: TonCompteur;
  children: ReactNode;
  /** Classes de placement (`absolute …`), propres à l'appelant. */
  position?: string;
  title?: string;
  "aria-label"?: string;
  "aria-hidden"?: boolean | "true" | "false";
  "data-badge"?: string;
}

export default function Compteur({ ton, children, position = "", ...reste }: CompteurProps) {
  return (
    <span
      {...reste}
      className={`${position} min-w-4 rounded-full px-1 text-center text-micro font-medium leading-4 ${TONS[ton]}`.trim()}
    >
      {children}
    </span>
  );
}
