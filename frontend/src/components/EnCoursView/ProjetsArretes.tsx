import { useState } from "react";
import type { ProjectOverview } from "../../types/api";
import Spinner from "./Spinner";

/** Au-delà, la section « Arrêtés » démarre repliée. */
export const SEUIL_REPLI = 5;

interface ProjetsArretesProps {
  projets: ProjectOverview[];
  enLancement: (projectId: string) => boolean;
  onLancer: (projectId: string) => void;
}

/**
 * Les projets qui déclarent des services et n'ont plus aucune app — ticket-424.
 *
 * « Lancer » passe par les services déclarés dans `agents.json` : une app
 * lancée à la main ne revient pas avec sa commande d'origine.
 */
export default function ProjetsArretes({ projets, enLancement, onLancer }: ProjetsArretesProps) {
  const [choix, setChoix] = useState<boolean | null>(null);
  if (projets.length === 0) return null;
  const ouverte = choix ?? projets.length <= SEUIL_REPLI;

  return (
    <section className="mb-4" aria-label="Arrêtés">
      <button
        type="button"
        aria-expanded={ouverte}
        onClick={() => setChoix(!ouverte)}
        className="mb-1 text-xs font-semibold text-zinc-400 hover:text-zinc-200"
      >
        Arrêtés ({projets.length})
      </button>
      {ouverte && (
        <ul className="rounded-sm bg-zinc-900 ring-1 ring-zinc-800">
          {projets.map((projet) => (
            <li
              key={projet.id}
              className="flex items-center justify-between border-t border-zinc-800 px-3 py-2 text-sm first:border-t-0"
            >
              <span className="font-medium text-zinc-100">{projet.name}</span>
              <button
                type="button"
                disabled={enLancement(projet.id)}
                onClick={() => onLancer(projet.id)}
                aria-label={`Lancer ${projet.name}`}
                className="flex items-center gap-1.5 rounded-sm bg-zinc-700 px-2 py-1 text-xs text-zinc-200 hover:bg-zinc-600 disabled:opacity-60"
              >
                {enLancement(projet.id) && <Spinner />}
                {enLancement(projet.id) ? "Lancement…" : "Lancer"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
