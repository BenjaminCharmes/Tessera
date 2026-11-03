/**
 * Sélecteur de vue — ticket-439.
 *
 * Groupe à fond surface, l'option active en surface-haute. Remplace les trois
 * copies de l'Historique, des Fichiers et des Agents.
 */
export interface OptionVue<V extends string> {
  valeur: V;
  libelle: string;
}

interface ViewSwitcherProps<V extends string> {
  options: OptionVue<V>[];
  valeur: V;
  onChange: (valeur: V) => void;
  /** Nom accessible du groupe. */
  label?: string;
}

export default function ViewSwitcher<V extends string>({
  options,
  valeur,
  onChange,
  label = "Vue",
}: ViewSwitcherProps<V>) {
  return (
    <div
      role="group"
      aria-label={label}
      className="flex gap-0.5 rounded-md bg-zinc-900 p-0.5 ring-1 ring-zinc-800"
    >
      {options.map((option) => (
        <button
          key={option.valeur}
          type="button"
          aria-pressed={valeur === option.valeur}
          onClick={() => onChange(option.valeur)}
          className={`rounded-sm px-3 py-1 text-xs transition-colors ${
            valeur === option.valeur
              ? "bg-zinc-800 text-zinc-100"
              : "text-zinc-400 hover:text-zinc-200"
          }`}
        >
          {option.libelle}
        </button>
      ))}
    </div>
  );
}
