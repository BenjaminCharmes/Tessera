import { useState } from "react";
import type { ProjectOverview } from "../../types/api";
import Button from "../../design/ui/Button";
import { IconChevronDown, IconChevronRight } from "../../design/icons";
import Spinner from "./Spinner";

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
 *
 * Dépliée par défaut : repliée, la section se réduisait à un mot sur une page
 * vide, et rien ne disait qu'elle s'ouvrait. Le chevron dit qu'elle se replie.
 */
export default function ProjetsArretes({ projets, enLancement, onLancer }: ProjetsArretesProps) {
  const [ouverte, setOuverte] = useState(true);
  if (projets.length === 0) return null;
  const Chevron = ouverte ? IconChevronDown : IconChevronRight;

  return (
    <section className="mb-4" aria-label="Arrêtés">
      <button
        type="button"
        aria-expanded={ouverte}
        onClick={() => setOuverte(!ouverte)}
        title={ouverte ? "Replier" : "Déplier"}
        className="mb-1 flex items-center gap-1 text-xs font-semibold text-zinc-400 hover:text-zinc-200"
      >
        <Chevron size={14} aria-hidden="true" />
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
              <Button
                taille="compact"
                disabled={enLancement(projet.id)}
                onClick={() => onLancer(projet.id)}
                aria-label={`Lancer ${projet.name}`}
              >
                {enLancement(projet.id) && <Spinner />}
                {enLancement(projet.id) ? "Lancement…" : "Lancer"}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
