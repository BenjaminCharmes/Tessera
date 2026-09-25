/**
 * La file de tickets sélectionnés (ticket-074).
 *
 * Le backend savait déjà enchaîner, mais rien ne l'exposait : on lançait les
 * tickets un par un, en surveillant l'écran pour savoir quand relancer.
 *
 * L'ordre affiché est celui d'exécution, et c'est celui de la sélection — pas
 * celui de la liste. Un lot produit par le planificateur a presque toujours des
 * dépendances, et c'est à l'utilisateur de dire dans quel ordre il les veut.
 *
 * **Un ticket non approuvé arrête la file** : enchaîner sur une base que
 * personne n'a validée ferait travailler le suivant sur un état douteux.
 */
interface QueueBarProps {
  selection: string[];
  onRun: () => void;
  onClear: () => void;
  enCours: boolean;
}

export default function QueueBar({
  selection,
  onRun,
  onClear,
  enCours,
}: QueueBarProps) {
  if (selection.length === 0) return null;

  return (
    <div className="border-b border-zinc-800 bg-zinc-900 px-3 py-2">
      <p className="mb-1 text-mini text-zinc-300">
        {selection.length} ticket{selection.length > 1 ? "s" : ""} en file
      </p>
      <p className="mb-2 truncate font-mono text-micro text-zinc-500">
        {selection.join(", ")}
      </p>
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={onRun}
          disabled={enCours}
          className="rounded-sm border border-violet-500/50 bg-violet-500/15 px-2 py-1 text-mini text-violet-200 transition-colors hover:border-violet-400 disabled:opacity-50"
        >
          Lancer la file
        </button>
        <button
          type="button"
          onClick={onClear}
          className="rounded-sm px-2 py-1 text-mini text-zinc-500 transition-colors hover:text-zinc-300"
        >
          Vider
        </button>
      </div>
      <p className="mt-1.5 text-micro text-zinc-600">
        Un ticket non approuvé arrête la file.
      </p>
    </div>
  );
}
