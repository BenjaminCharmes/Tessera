import type { ReactNode } from "react";

interface SalleProps {
  titre: string;
  /** Ce que dit la salle quand personne n'y est. */
  vide: string;
  /** Les occupants : une salle sans enfant dit `vide`. */
  children?: ReactNode[];
}

/** Le cadre commun des salles : un titre, ses occupants ou une ligne qui dit qu'elle est libre. */
export default function Salle({ titre, vide, children = [] }: SalleProps) {
  const occupee = children.length > 0;
  return (
    <aside
      aria-label={titre}
      data-occupee={occupee}
      className="min-w-0 flex-1 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2"
    >
      <h3 className="text-micro uppercase tracking-wide text-zinc-500">{titre}</h3>
      {occupee ? <ul className="mt-1 flex flex-col gap-1">{children}</ul> : <p className="mt-1 text-xs text-zinc-500">{vide}</p>}
    </aside>
  );
}
