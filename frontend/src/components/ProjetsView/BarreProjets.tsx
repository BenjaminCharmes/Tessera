import {
  TRIS,
  type FiltresProjets,
  type PastilleDeCategorie,
  type TriDesProjets,
} from "./organiser";

interface BarreProjetsProps {
  filtres: FiltresProjets;
  pastilles: PastilleDeCategorie[];
  /** Nombre de projets, toutes catégories confondues. */
  total: number;
  onChange: (f: FiltresProjets) => void;
}

const CHAMP =
  "rounded-sm border border-zinc-700 bg-zinc-950 px-2 py-1 text-xs text-zinc-300 outline-hidden focus:border-zinc-500";

function Pastille({
  libelle,
  nombre,
  active,
  onClick,
}: {
  libelle: string;
  nombre: number;
  active: boolean;
  onClick: () => void;
}) {
  // Sélection = interaction : fond violet, jamais texte violet (ADR-026).
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`rounded-full px-2.5 py-0.5 text-micro transition-colors ${
        active
          ? "bg-violet-500/20 text-zinc-100"
          : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
      }`}
    >
      {libelle} <span className="font-medium">{nombre}</span>
    </button>
  );
}

/** Recherche, pastilles de catégorie et tri de la vue Projets — ticket-399. */
export default function BarreProjets({
  filtres,
  pastilles,
  total,
  onChange,
}: BarreProjetsProps) {
  return (
    <div className="flex flex-col gap-2 border-b border-zinc-800 px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="search"
          aria-label="Chercher un projet"
          placeholder="Chercher (nom, identifiant, description)"
          value={filtres.recherche}
          onChange={(e) => onChange({ ...filtres, recherche: e.target.value })}
          className={`${CHAMP} min-w-64 flex-1`}
        />
        <select
          aria-label="Trier les projets"
          value={filtres.tri}
          onChange={(e) =>
            onChange({ ...filtres, tri: e.target.value as TriDesProjets })
          }
          className={CHAMP}
        >
          {TRIS.map((t) => (
            <option key={t.valeur} value={t.valeur}>
              {t.libelle}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-wrap gap-1.5">
        <Pastille
          libelle="Toutes"
          nombre={total}
          active={filtres.categorie === null}
          onClick={() => onChange({ ...filtres, categorie: null })}
        />
        {pastilles.map((p) => (
          <Pastille
            key={p.valeur}
            libelle={p.libelle}
            nombre={p.nombre}
            active={filtres.categorie === p.valeur}
            onClick={() => onChange({ ...filtres, categorie: p.valeur })}
          />
        ))}
      </div>
    </div>
  );
}
