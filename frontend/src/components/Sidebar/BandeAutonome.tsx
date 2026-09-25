import { useState } from "react";

/**
 * Laisser l'IDE choisir lui-même les tickets à enchaîner (ticket-089).
 *
 * Le mode autonome existait côté backend depuis longtemps et n'avait aucun
 * bouton : `run_autonomous` choisit le prochain ticket par priorité et par
 * dépendances, et `depuis_github` peut d'abord tirer les issues `agent-ready`.
 * Sans surface, c'était du code que personne ne pouvait atteindre.
 *
 * Il prend la place de la file quand la sélection est vide : les deux répondent
 * à la même question — quels tickets, dans quel ordre — et la différence est
 * qui tranche. Les montrer ensemble demanderait de choisir entre deux réponses
 * à la même chose.
 */
interface BandeAutonomeProps {
  selectionVide: boolean;
  /** Sans dépôt lié, tirer des issues n'a aucun sens. */
  githubLie: boolean;
  enCours: boolean;
  onLancer: (options: { depuisGithub: boolean }) => void;
}

export default function BandeAutonome({
  selectionVide,
  githubLie,
  enCours,
  onLancer,
}: BandeAutonomeProps) {
  const [depuisGithub, setDepuisGithub] = useState(false);

  if (!selectionVide) return null;

  return (
    <div className="border-b border-zinc-800 bg-zinc-900 px-3 py-2">
      <p className="mb-2 text-micro text-zinc-500">
        Aucun ticket en file. L'IDE peut en choisir lui-même, par priorité et
        dépendances.
      </p>
      {githubLie && (
        <label className="mb-2 flex items-center gap-1.5 text-micro text-zinc-400">
          <input
            type="checkbox"
            checked={depuisGithub}
            onChange={(e) => setDepuisGithub(e.target.checked)}
            className="accent-violet-500"
          />
          Partir des issues GitHub étiquetées agent-ready
        </label>
      )}
      <button
        type="button"
        onClick={() => onLancer({ depuisGithub })}
        disabled={enCours}
        className="rounded-sm border border-zinc-700 px-2 py-1 text-mini text-zinc-300 transition-colors hover:border-zinc-500 disabled:opacity-50"
      >
        Laisser l'IDE enchaîner
      </button>
    </div>
  );
}
