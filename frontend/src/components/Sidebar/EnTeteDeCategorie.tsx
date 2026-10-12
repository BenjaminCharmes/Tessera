import { IconChevronDown } from "../../design/icons";
import type { Project } from "../../types/api";
import { resumeDeCategorie } from "./resumeDeCategorie";

interface EnTeteDeCategorieProps {
  /** `null` : les projets qui ne déclarent aucune catégorie. */
  categorie: string | null;
  projets: Project[];
  repliee: boolean;
  onBasculer: () => void;
}

/**
 * Le titre d'une catégorie, devenu bouton — ticket-400.
 *
 * Partagé par la barre latérale et la vue « Projets ». Un intitulé de groupe est
 * un titre de région : ADR-026 lui donne le neutre, le badge aussi (zinc).
 */
export default function EnTeteDeCategorie({
  categorie,
  projets,
  repliee,
  onBasculer,
}: EnTeteDeCategorieProps) {
  return (
    <button
      type="button"
      onClick={onBasculer}
      aria-expanded={!repliee}
      title={repliee ? resumeDeCategorie(projets) : undefined}
      className="flex w-full items-center gap-1 px-3 pb-1 pt-3 text-left text-micro uppercase tracking-wide text-zinc-600 transition-colors hover:text-zinc-400"
    >
      <IconChevronDown
        size={12}
        className={`shrink-0 transition-transform ${repliee ? "-rotate-90" : ""}`}
      />
      <span className="flex-1 truncate">{categorie ?? "Sans catégorie"}</span>
      {repliee && (
        <span className="shrink-0 rounded-sm bg-zinc-800 px-1.5 py-0.5 text-zinc-400">
          {projets.length}
        </span>
      )}
    </button>
  );
}
