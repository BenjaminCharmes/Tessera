import { useState, type FormEvent } from "react";
import { IconFolder } from "../../design/icons";

interface MenuCategorieProps {
  /** Le nom du projet, pour nommer le bouton. */
  projet: string;
  /** La catégorie actuelle, `null` si le projet n'en a pas. */
  actuelle: string | null;
  /** Les catégories existantes, tous projets confondus. */
  categories: string[];
  /** Une chaîne vide retire la catégorie. */
  onChoisir: (categorie: string) => void;
}

const ITEM =
  "block w-full truncate rounded-sm px-2 py-1 text-left text-micro text-zinc-300 hover:bg-zinc-800";

/**
 * Le menu qui change la catégorie d'un projet — ticket-399.
 *
 * Il vit dans la carte sans la déclencher : ni le clic ni le clavier ne
 * remontent, sinon changer de catégorie sélectionnerait aussi le projet.
 */
export default function MenuCategorie({
  projet,
  actuelle,
  categories,
  onChoisir,
}: MenuCategorieProps) {
  const [ouvert, setOuvert] = useState(false);
  const [nouvelle, setNouvelle] = useState("");

  function choisir(categorie: string) {
    setOuvert(false);
    setNouvelle("");
    onChoisir(categorie);
  }

  function creer(e: FormEvent) {
    e.preventDefault();
    const nom = nouvelle.trim();
    if (nom !== "") choisir(nom);
  }

  return (
    <div
      className="relative"
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
    >
      <button
        type="button"
        aria-label={`Changer la catégorie de ${projet}`}
        aria-expanded={ouvert}
        onClick={() => setOuvert((o) => !o)}
        className="flex size-6 items-center justify-center rounded-sm text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-zinc-200"
      >
        <IconFolder size={14} />
      </button>
      {ouvert && (
        <div
          role="menu"
          aria-label={`Catégorie de ${projet}`}
          className="absolute right-0 z-10 mt-1 flex w-48 flex-col gap-0.5 rounded-sm border border-zinc-700 bg-zinc-900 p-1 shadow-lg"
        >
          {categories
            .filter((c) => c !== actuelle)
            .map((c) => (
              <button key={c} type="button" role="menuitem" className={ITEM} onClick={() => choisir(c)}>
                {c}
              </button>
            ))}
          <form onSubmit={creer} className="flex gap-1 border-t border-zinc-800 pt-1">
            <input
              aria-label="Nouvelle catégorie"
              placeholder="Nouvelle catégorie"
              value={nouvelle}
              onChange={(e) => setNouvelle(e.target.value)}
              className="min-w-0 flex-1 rounded-sm border border-zinc-700 bg-zinc-950 px-1.5 py-0.5 text-micro text-zinc-300 outline-hidden focus:border-zinc-500"
            />
            <button
              type="submit"
              disabled={nouvelle.trim() === ""}
              className="rounded-sm bg-zinc-700 px-1.5 text-micro text-zinc-200 hover:bg-zinc-600 disabled:opacity-40"
            >
              Créer
            </button>
          </form>
          {actuelle !== null && (
            <button type="button" role="menuitem" className={`${ITEM} border-t border-zinc-800`} onClick={() => choisir("")}>
              Retirer de la catégorie
            </button>
          )}
        </div>
      )}
    </div>
  );
}
