import type { ReactNode } from "react";

interface SalleProps {
  titre: string;
  /** Ce que la salle accueille, en une phrase sous son titre. */
  entete: string;
  /** Ce que dit la salle quand personne n'y est. */
  vide: string;
  /** Le mobilier : la salle elle-même, dessiné occupée ou non (ADR-058). */
  mobilier: ReactNode;
  /** Les occupants : une salle sans enfant dit `vide`. */
  children?: ReactNode[];
}

/** Un sol en lames : deux tons du jeton de sol, rien d'animé. */
const SOL = {
  backgroundImage:
    "repeating-linear-gradient(90deg, var(--sprite-sol) 0 22px, var(--sprite-sol-lame) 22px 24px)",
};

/** Le cadre commun des salles : titre, sol et mobilier toujours là, occupants à côté, ou la ligne qui dit qu'elle est libre. */
export default function Salle({ titre, entete, vide, mobilier, children = [] }: SalleProps) {
  const occupee = children.length > 0;
  return (
    <aside
      aria-label={titre}
      data-occupee={occupee}
      className="min-w-0 flex-1 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2"
    >
      <h3 className="text-micro uppercase tracking-wide text-zinc-500">{titre}</h3>
      <p className="text-micro text-zinc-500">{entete}</p>
      <div style={SOL} className="mt-2 flex min-h-[132px] items-center gap-4 rounded px-3 py-2">
        <div className="shrink-0">{mobilier}</div>
        {occupee && <ul className="flex min-w-0 flex-col gap-1">{children}</ul>}
      </div>
      {!occupee && <p className="mt-1 text-xs text-zinc-500">{vide}</p>}
    </aside>
  );
}
