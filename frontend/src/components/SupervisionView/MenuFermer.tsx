import { useState } from "react";
import type { IssueDuRun } from "./issueDuRun";

/** Une entrée du menu de fermeture par lot. */
export interface EntreeMenuFermer {
  /** Libellé affiché, sans le compte (ex. « Les bloqués »). */
  label: string;
  /** Issue cible — null signifie « tous les runs clos ». */
  issue: IssueDuRun | null;
  /** Nombre de runs concernés. L'entrée est désactivée quand il vaut 0. */
  count: number;
}

interface MenuFermerProps {
  entrees: EntreeMenuFermer[];
  onFermer: (issue: IssueDuRun | null) => void;
}

/**
 * Menu déroulant « Fermer… » pour fermer des runs clos par lot (ticket-344).
 *
 * Affiché dans la bande d'en-tête de SupervisionView. Chaque entrée est
 * désactivée quand son compte vaut zéro, ce qui évite de proposer une action
 * sans effet.
 */
export default function MenuFermer({ entrees, onFermer }: MenuFermerProps) {
  const [ouvert, setOuvert] = useState(false);

  return (
    <div className="relative">
      <button
        type="button"
        aria-label="Fermer par lot"
        aria-haspopup="true"
        aria-expanded={ouvert}
        onClick={() => setOuvert((o) => !o)}
        className="text-xs text-zinc-400 hover:text-zinc-200"
      >
        Fermer…
      </button>

      {ouvert && (
        <div
          role="menu"
          className="absolute right-0 top-full z-10 min-w-44 rounded border border-zinc-700 bg-zinc-800 py-1 shadow-lg"
        >
          {entrees.map(({ label, issue, count }) => (
            <button
              key={issue ?? "tous"}
              type="button"
              role="menuitem"
              disabled={count === 0}
              onClick={() => {
                onFermer(issue);
                setOuvert(false);
              }}
              className="w-full cursor-pointer px-3 py-1.5 text-left text-xs text-zinc-300 hover:bg-zinc-700 disabled:cursor-not-allowed disabled:text-zinc-600"
            >
              {label} ({count})
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
