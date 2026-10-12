import { IconProject } from "../../design/icons";
import { lienDuDepot } from "../../lib/lienDuDepot";
import type { Project } from "../../types/api";

interface LigneDeProjetProps {
  project: Project;
  active: boolean;
  /** Un run de ce projet attend une réponse (ticket-186). */
  enAttente: boolean;
  onSelect: () => void;
}

/**
 * Une ligne de la liste des projets : le bouton de sélection et, à côté, le
 * raccourci vers le dépôt.
 *
 * Le lien GitHub est un voisin du bouton, pas son enfant : un `<a>` dans un
 * `<button>` est du HTML invalide, et deux cibles imbriquées se disputent le
 * clic et le focus (ticket-123).
 */
export default function LigneDeProjet({
  project,
  active,
  enAttente,
  onSelect,
}: LigneDeProjetProps) {
  return (
    <div
      className={`flex items-center transition-colors ${
        active ? "bg-zinc-700 text-white" : "hover:bg-zinc-800 text-zinc-300"
      }`}
    >
      <button
        type="button"
        onClick={onSelect}
        className="flex min-w-0 flex-1 items-center gap-2 px-3 py-2 text-left"
      >
        <IconProject size={12} className="shrink-0 text-zinc-500" />
        <span className="truncate flex-1">{project.name}</span>
        {/* Ambre : une attente, au sens d'ADR-026. Visible depuis n'importe
            quel onglet, ce que ni le panneau ni la carte de Supervision ne
            permettaient (ticket-186). */}
        {enAttente && (
          <span
            className="size-1.5 shrink-0 rounded-full bg-amber-400"
            title="Un agent attend une réponse"
            aria-label="Un agent attend une réponse"
          />
        )}
      </button>
      <LienDuDepot project={project} />
    </div>
  );
}

/**
 * Le raccourci vers le dépôt d'un projet, quand il en a un d'ouvrable.
 *
 * `github_remote` vaut `owner/repo` : posée telle quelle en `href`, elle se
 * résolvait contre l'origine de l'app et le lien menait à une page de l'IDE
 * (ticket-184).
 */
function LienDuDepot({ project }: { project: Project }) {
  const lien = lienDuDepot(project.github_remote);
  if (!lien) return null;
  return (
    <a
      href={lien}
      target="_blank"
      rel="noopener noreferrer"
      className="shrink-0 px-3 py-2 text-xs leading-none text-zinc-500 transition-colors hover:text-zinc-200"
      title={lien}
      aria-label={`Ouvrir le repo GitHub de ${project.name}`}
    >
      GH
    </a>
  );
}
