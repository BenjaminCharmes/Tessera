import { useEffect, useRef, useState } from "react";
import { IconChevronDown, IconCross } from "../../design/icons";
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
 * Menu déroulant « Fermer » pour fermer des runs clos par lot (ticket-344).
 *
 * Affiché dans la bande d'en-tête de SupervisionView. Un simple lien de texte
 * passait inaperçu : le déclencheur a une bordure, une icône, le nombre de
 * runs clos et un chevron, pour se lire comme un menu. Chaque entrée est
 * désactivée quand son compte vaut zéro, ce qui évite de proposer une action
 * sans effet. Échap ou un clic à côté referment le menu.
 */
export default function MenuFermer({ entrees, onFermer }: MenuFermerProps) {
  const [ouvert, setOuvert] = useState(false);
  const racine = useRef<HTMLDivElement>(null);
  const totalClos = entrees.find((e) => e.issue === null)?.count ?? 0;

  useEffect(() => {
    if (!ouvert) return;
    const surClic = (e: MouseEvent) => {
      if (racine.current && !racine.current.contains(e.target as Node)) {
        setOuvert(false);
      }
    };
    const surTouche = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOuvert(false);
    };
    document.addEventListener("mousedown", surClic);
    document.addEventListener("keydown", surTouche);
    return () => {
      document.removeEventListener("mousedown", surClic);
      document.removeEventListener("keydown", surTouche);
    };
  }, [ouvert]);

  return (
    <div ref={racine} className="relative">
      <button
        type="button"
        aria-label="Fermer par lot"
        aria-haspopup="true"
        aria-expanded={ouvert}
        onClick={() => setOuvert((o) => !o)}
        className={`inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-xs transition-colors ${
          ouvert
            ? "border-zinc-500 bg-zinc-800 text-zinc-100"
            : "border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:bg-zinc-800 hover:text-zinc-100"
        }`}
      >
        <IconCross size={12} />
        Fermer
        <span className="rounded-sm bg-zinc-700 px-1 text-micro tabular-nums text-zinc-200">
          {totalClos}
        </span>
        <IconChevronDown
          size={12}
          className={`transition-transform ${ouvert ? "rotate-180" : ""}`}
        />
      </button>

      {ouvert && (
        <div
          role="menu"
          className="absolute right-0 top-full z-10 mt-1 min-w-44 rounded-sm border border-zinc-700 bg-zinc-800 py-1 shadow-lg"
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
