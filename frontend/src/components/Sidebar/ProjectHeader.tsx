import { BAND } from "../../design/layout";
import type { Project } from "../../types/api";

/**
 * En-tête du projet actif, épinglé au-dessus de la colonne qui défile
 * (ticket-065).
 *
 * Les actions d'un projet — lier un dépôt, choisir le mode des artefacts, le
 * retirer de l'IDE — vivaient sous la liste des tickets. Sur un projet qui en
 * a trente, elles étaient à un écran et demi de défilement, sans que rien
 * n'annonce leur existence. Elles remontent ici, à un endroit qui ne bouge
 * jamais.
 *
 * L'ouverture dans VSCode est un simple lien `vscode://` : c'est le geste
 * central du pivot cockpit — Tessera pilote, VSCode édite — et il ne coûte
 * aucun aller-retour avec le backend.
 */
interface ProjectHeaderProps {
  project: Project | null;
  gitOuvert: boolean;
  onBasculerGit: () => void;
}

/** `vscode://file/` attend des séparateurs POSIX, y compris sous Windows. */
function lienVSCode(chemin: string): string {
  return `vscode://file/${chemin.replace(/\\/g, "/")}`;
}

export default function ProjectHeader({
  project,
  gitOuvert,
  onBasculerGit,
}: ProjectHeaderProps) {
  if (!project) {
    return (
      <header className={`${BAND} border-b border-zinc-800 px-3`}>
        <p className="text-xs text-zinc-500">Aucun projet sélectionné</p>
      </header>
    );
  }

  return (
    <header
      className={`${BAND} justify-between gap-2 border-b border-zinc-800 px-3`}
    >
      {/* Une seule ligne : l'en-tête doit tenir dans la bande commune pour
          s'aligner avec celles du centre et de la colonne de droite. Le
          chemin complet passe en infobulle plutôt qu'en seconde ligne. */}
      <h2
        className="truncate text-sm font-medium text-violet-100"
        title={`${project.id} — ${project.path ?? ""}`}
      >
        {project.name}
      </h2>

      <div className="flex shrink-0 items-center gap-1.5">
        {/* Un projet sans chemin ne coûte que ce bouton : le faire planter
            emportait toute la colonne derrière l'ErrorBoundary. */}
        {project.path ? (
          <a
            href={lienVSCode(project.path)}
            className="whitespace-nowrap rounded-sm border border-zinc-700 px-2 py-1 text-mini text-zinc-300 transition-colors hover:border-zinc-500 hover:text-zinc-100"
          >
            VSCode
          </a>
        ) : null}
        <button
          type="button"
          onClick={onBasculerGit}
          aria-expanded={gitOuvert}
          className={`whitespace-nowrap rounded border px-2 py-1 text-mini transition-colors ${
            gitOuvert
              ? "border-zinc-500 bg-zinc-800 text-zinc-100"
              : "border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:text-zinc-100"
          }`}
        >
          Git
        </button>
      </div>
    </header>
  );
}
