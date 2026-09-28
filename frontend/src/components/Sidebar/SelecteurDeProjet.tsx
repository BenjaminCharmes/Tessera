import { useEffect, useRef, useState } from "react";
import { IconChevronDown } from "../../design/icons";
import { useProjects } from "../../hooks/useProjects";
import type { Project } from "../../types/api";
import RemoveProjectModal from "./RemoveProjectModal";

/**
 * Changer de projet sans quitter la vue courante — ticket-174.
 *
 * Le nom du projet était un titre ; c'est maintenant le déclencheur. Changer
 * de projet imposait un aller-retour par l'onglet « Projets », qui fait perdre
 * ce qu'on regardait — Tickets, Supervision, Statistiques. À neuf projets et avec des
 * runs en parallèle (ADR-038), c'est le geste le plus fréquent d'une session.
 *
 * ADR-026 : le nom reste en `violet-100` — l'identité — et la liste n'emprunte
 * qu'au neutre. Un projet sélectionné se marque par une barre, jamais par la
 * couleur de son nom.
 */
interface SelecteurDeProjetProps {
  project: Project;
  onSelectProject: (project: Project) => void;
}

export default function SelecteurDeProjet({
  project,
  onSelectProject,
}: SelecteurDeProjetProps) {
  const [ouvert, setOuvert] = useState(false);
  const [retrait, setRetrait] = useState(false);
  const { projects } = useProjects();
  const conteneur = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!ouvert) return;
    // Échap et le clic en dehors : sans eux, la liste reste ouverte par-dessus
    // ce qu'on voulait justement continuer de regarder.
    function surTouche(e: KeyboardEvent) {
      if (e.key === "Escape") setOuvert(false);
    }
    function surClic(e: MouseEvent) {
      if (!conteneur.current?.contains(e.target as Node)) setOuvert(false);
    }
    document.addEventListener("keydown", surTouche);
    document.addEventListener("mousedown", surClic);
    return () => {
      document.removeEventListener("keydown", surTouche);
      document.removeEventListener("mousedown", surClic);
    };
  }, [ouvert]);

  return (
    <div ref={conteneur} className="relative min-w-0">
      <button
        type="button"
        onClick={() => setOuvert((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={ouvert}
        title={`${project.id} — ${project.path ?? ""}`}
        className="flex min-w-0 max-w-full items-center gap-1 truncate text-sm font-medium text-violet-100 transition-colors hover:text-violet-50"
      >
        <span className="truncate">{project.name}</span>
        {/* ADR-026 : les affordances viennent de `design/icons.tsx`, jamais
            d'un glyphe — un test le verrouille. */}
        <IconChevronDown size={12} className="shrink-0 text-zinc-500" />
      </button>

      {ouvert ? (
        <div className="absolute left-0 top-full z-20 mt-1 w-64 rounded-md border border-zinc-700 bg-zinc-900 py-1 shadow-lg">
          <ul
            role="listbox"
            aria-label="Projets"
            className="max-h-72 overflow-y-auto"
          >
            {projects.map((p) => {
              const actif = p.id === project.id;
              return (
                <li key={p.id}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={actif}
                    onClick={() => {
                      onSelectProject(p);
                      setOuvert(false);
                    }}
                    className={`flex w-full items-center gap-2 px-2 py-1.5 text-left text-xs transition-colors hover:bg-zinc-800 ${
                      actif ? "text-zinc-100" : "text-zinc-400"
                    }`}
                  >
                    <span
                      aria-hidden
                      className={`h-3 w-0.5 shrink-0 rounded-full ${
                        actif ? "bg-violet-400" : "bg-transparent"
                      }`}
                    />
                    <span className="truncate">{p.name}</span>
                  </button>
                </li>
              );
            })}
          </ul>
          {/* Hors de la `listbox` : c'est une action sur le projet actif, pas
              un projet à choisir. Elle vivait au pied du panneau Git, où
              rien ne l'annonçait (ticket-205). */}
          <div className="mt-1 border-t border-zinc-800 pt-1">
            <button
              type="button"
              onClick={() => {
                setOuvert(false);
                setRetrait(true);
              }}
              className="w-full px-2 py-1.5 text-left text-xs text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-zinc-300"
            >
              Retirer ce projet de l'IDE…
            </button>
          </div>
        </div>
      ) : null}

      {retrait ? (
        <RemoveProjectModal
          project={project}
          onClose={() => setRetrait(false)}
          onRemoved={() => {
            setRetrait(false);
            // Le projet n'existe plus : la liste doit repartir du serveur.
            window.location.reload();
          }}
        />
      ) : null}
    </div>
  );
}
